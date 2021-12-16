from gql import gql, Client
from gql.transport.aiohttp import AIOHTTPTransport

pairsQuery = gql(
    """
    query {
        pairs(offset: 0, limit: 10) {
            firstToken {
                name
                identifier
            }
            firstTokenPrice
            firstTokenPriceUSD
            secondToken {
                name
                identifier
            }
            secondTokenPrice
            secondTokenPriceUSD
            address
            totalFeePercent
            info {
                reserves0
                reserves1
            }
        }
    }
"""
)

queryWrappingInfo = gql(
    '''
    query {
        wrappingInfo{
              shard
              address
              wrappedToken {
                    name
              }
        }
    }
'''
)

queryGetAmountOut = gql(
    '''
    query ($amount: String!, $tokenInID: String!, $pairAddress: String!) {
        getAmountOut(amount: $amount, tokenInID: $tokenInID, pairAddress: $pairAddress)
    }
'''
)


def query(query_string, variables):
    ht = AIOHTTPTransport(url=graphqlURL)
    queryClient = Client(transport=ht, fetch_schema_from_transport=False)

    return queryClient.execute(query_string, variable_values=variables)


def string2hex(string):
    return string.encode("utf-8").hex()


def int2hex(value):
    r = hex(value)[2:]
    if len(r) % 2 == 1:
        r = '0' + r
    return r


#graphqlURL = "https://testnet-exchange-graph.elrond.com/graphql"  # https://graph.maiar.exchange/graphql https://testnet-exchange-graph.elrond.com/graphql
graphqlURL = "https://testnet-exchange-graph.elrond.com/graphql"
chainID = 'T'  # '1'

net = ''
if chainID == 'D':
    net = 'devnet-'
elif chainID == 'T':
    net = 'testnet-'

accInfoURL = f'https://{net}api.elrond.com/accounts/'
gateaway = f'https://{net}gateway.elrond.com'

wrapEgldTI = 'WEGLD-f643d8'  # WEGLD-f643d8 WEGLD-bd4d79
rideTI = 'RIDE-ae50f0'  # RIDE-ae50f0 RIDE-7d18e9