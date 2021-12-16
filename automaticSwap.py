import time

from gql import gql

from dex_manager import DexManager
from logger import Logger
from utils import query, gateaway, wrapEgldTI, rideTI

queryWrappingInfo = gql(
    '''
    query {
            pairs(offset: 2, limit: 3) {
                firstToken {
                    identifier
                }
                secondToken {
                    identifier
                }
                state
            }
    }

'''
)


if __name__ == '__main__':

    while True:
        time.sleep(0.5)
        try:
            r = query(queryWrappingInfo, None)
            print(r)
            if r['pairs'][0]['state'] == 'Active':
                logger = Logger(logging_service='DexManager')
                logger.info("Starting")

                dexManager = DexManager(
                    pem_file="dexswap.pem",
                    gateaway=gateaway,
                    logger=logger,
                )
                print(dexManager.swap(wrapEgldTI, rideTI, 105 * 10 ** 18))
        except Exception as e:
            print(e)
