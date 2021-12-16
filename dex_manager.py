from multiprocessing import Lock

import requests
from erdpy.accounts import Account
from erdpy.proxy import ElrondProxy
from erdpy.transactions import Transaction

from logger import Logger
from utils import *


class DexManager:
    def __init__(self, pem_file, gateaway, logger: Logger):
        self.mutex = Lock()
        self.account = Account(pem_file=pem_file)
        self.proxy = ElrondProxy(gateaway)
        self.logger = logger
        self.logger.info(f"gateway: {gateaway}")
        self.pairs = {}
        self.tokenIdentifiers = {}
        self.fetch_pairs()
        self.wrapperContract = self.getWrapperContract()

    def getShardAccount(self, address=None):
        if address is None:
            address = self.account.address.bech32()

        response = requests.get(accInfoURL + address)
        errorMessage = ''
        if response.status_code != 200:
            errorMessage = "fail to fetch account infos"
        jsonResponse = response.json()
        if 'shard' not in jsonResponse:
            errorMessage = "no shard id info in account infos"

        if errorMessage != '':
            self.logger.error(errorMessage)
            raise Exception(errorMessage)
        return jsonResponse['shard']

    def fetch_pairs(self):
        with self.mutex:
            pairs = query(pairsQuery, None)['pairs']

            for pair in pairs:
                pairAddress = pair['address']
                fee = pair['totalFeePercent']

                ftn = pair['firstToken']['name']
                fti = pair['firstToken']['identifier']
                ftp = float(pair['firstTokenPrice'])
                ftpUSD = float(pair['firstTokenPriceUSD'])

                stn = pair['secondToken']['name']
                sti = pair['secondToken']['identifier']
                stp = float(pair['secondTokenPrice'])
                stpUSD = float(pair['secondTokenPriceUSD'])

                fts = int(pair['info']['reserves0'])
                sts = int(pair['info']['reserves1'])
                self.pairs[pairAddress] = {
                    fti: {
                        'name': ftn,
                        'supply': fts,
                        'price': ftp,  # in secondToken
                        'priceUSD': ftpUSD
                    },
                    sti: {
                        'name': stn,
                        'supply': sts,
                        'price': stp,  # in firstToken
                        'priceUSD': stpUSD
                    },
                    'fee': fee
                }

                if ftn not in self.tokenIdentifiers:
                    self.tokenIdentifiers[ftn] = fti

                if stn not in self.tokenIdentifiers:
                    self.tokenIdentifiers[stn] = sti

    def getWrapperContract(self):
        contracts = query(queryWrappingInfo, None)['wrappingInfo']
        for contract in contracts:
            if contract['shard'] == self.getShardAccount():
                return contract['address']
        return None

    def getTokenIdentifier(self, tokenName):
        tokenID = None
        with self.mutex:
            if tokenName in self.tokenIdentifiers:
                tokenID = self.tokenIdentifiers[tokenName]
        return tokenID

    def getPairAddress(self, tokenIN, tokenOUT):
        for pairAddress in self.pairs:
            if tokenIN in self.pairs[pairAddress] and tokenOUT in self.pairs[pairAddress]:
                return pairAddress
        return None

    def generateTx(self, data, gasLimit, value=0, receiver=None):
        sender = self.account.address.bech32()
        if receiver is None:
            receiver = self.account.address.bech32()
        nonce = self.proxy.get_account_nonce(self.account.address)

        tx = Transaction()
        tx.sender = sender
        tx.nonce = nonce
        tx.version = self.account
        tx.value = str(value)
        tx.receiver = receiver
        tx.chainID = chainID
        tx.gasPrice = 1000000000
        tx.gasLimit = gasLimit
        tx.version = 1
        tx.data = data
        return tx

    def sentTransaction(self, receiver, data, value, gasLimit):
        self.account.sync_nonce(self.proxy)
        tx = self.generateTx(
            receiver=receiver,
            data=data,
            value=value,
            gasLimit=gasLimit
        )
        tx.sign(self.account)
        print(f"trying to send transaction hash: {tx.hash}")
        try:
            tx = tx.send_wait_result(self.proxy, 700)
            if tx['status'] == 'success':
                self.logger.debug(f"transaction sent successfully: {tx['hash']}")
            elif tx['status'] == 'invalid':
                err = tx['receipt']['data']
                self.logger.debug(f"failed with reason: {err}")
            return tx['hash'], None
        except Exception as e:
            self.logger.error(e)
            return None, e

    def wrapEgld(self, value):
        value = value
        data = 'wrapEgld'
        return self.sentTransaction(
            receiver=self.wrapperContract,
            data=data,
            value=value,
            gasLimit=4000000
        )

    def unWrapEgld(self, value):
        data = '@'.join([
            'ESDTTransfer',
            string2hex(wrapEgldTI),
            int2hex(value),
            '756e7772617045676c64'  # unwrapEgld
        ])
        return self.sentTransaction(
            receiver=self.wrapperContract,
            data=data,
            value=0,
            gasLimit=4000000
        )

    def swap(self, tokenIN, tokenOUT, valueIN, valueOUT=None, slippage=0.01):
        pairAddress = self.getPairAddress(tokenIN, tokenOUT)
        if valueOUT is None:
            valueOUT = int(query(queryGetAmountOut, {
                "amount": str(valueIN),
                'tokenInID': tokenIN,
                'pairAddress': pairAddress
            })['getAmountOut'])

        valueOUT -= int(valueOUT * slippage)
        data = '@'.join([
            'ESDTTransfer',
            string2hex(tokenIN),
            int2hex(valueIN),
            '73776170546f6b656e734669786564496e707574',   # swapTokensFixedInput
            string2hex(tokenOUT),
            int2hex(valueOUT)
        ])
        self.logger.info(f"amount to pay: {valueIN} {tokenIN} for {valueOUT} {tokenOUT}")
        txHash, err = self.sentTransaction(
            receiver=pairAddress,
            data=data,
            value=0,
            gasLimit=20000000
        )

        if err is not None:
            self.logger.debug('swap failed')
        return txHash, err


if __name__ == '__main__':
    logger = Logger(logging_service='DexManager')
    logger.info("Starting")

    dexManager = DexManager(
        pem_file="dexswap.pem",
        gateaway=gateaway,
        logger=logger,
    )
    #print(dexManager.unWrapEgld(5 * 10 ** 18))
    print(dexManager.wrapEgld(int(1.6 * 10 ** 18)))
    #print(dexManager.swap(wrapEgldTI, rideTI, 10 * 10 ** 18))
