"""
    cluelessperson
    Requires: python-bitcoinlib by Peter Todd, that beautiful mofo

"""
import os, re, traceback
from datetime import datetime
import bitcoin.rpc
import znc

import traceback
import bitcoin.rpc
from bitcoin.core import lx

allowed_channels = [
    '#bitcoin',
    '##bitcoin',
    '#electrum',
    '#cluelessperson'
]

module_path = os.path.dirname(__file__)

class TX:
    def __init__(self, txid, rpc_conf_file=module_path+'/rpc.conf'):
        self.rpc_conf = {"btc_conf_file": rpc_conf_file}
        self.rpc = None
        self.height = 0
        self.txid = txid
        self.tx = None
        self.num_inputs = 0
        self.amt_input = 0
        self.num_outputs = 0
        self.amt_output = 0
        self.fee = 0
        self.bytes = 0
        self.kb = 0
        self.fee_byte = 0
        self.fee_kb = 0
        self.weight = 0
        self.fee_weight = 0
        self.locktime = 0
        self.block_height = None
        self.confirmations = 0
        self.datetime = None
        self.rbf = False

        self.lookup()
        self.breakdown()

    def lookup(self):
        self.rpc = bitcoin.rpc.Proxy(**self.rpc_conf)
        self.height = self.rpc.getblockcount()
        self.tx = self.rpc.getrawtransaction(lx(self.txid), verbose=True)

    def breakdown(self):
        self.num_inputs = len(self.tx['tx'].vin)
        for txin in self.tx['tx'].vin:
            self.amt_input += self.rpc.getrawtransaction(txin.prevout.hash).vout[txin.prevout.n].nValue
            if txin.nSequence < 0xfffffffe:
                self.rbf = True
        self.num_outputs = len(self.tx['tx'].vout)
        for txout in self.tx['tx'].vout:
            self.amt_output += txout.nValue
        self.fee = self.amt_input - self.amt_output
        self.bytes = len(self.tx['tx'].serialize())
        self.fee_kb = (self.fee * 1024) / self.bytes * 0.00000001
        self.fee_byte = self.fee // self.bytes
        self.weight = (self.bytes-len(self.tx['tx'].wit.serialize())) * 3 + self.bytes
        self.fee_weight = self.fee // self.weight
        self.locktime = self.tx['tx'].nLockTime
        if 'confirmations' in self.tx.keys():
            self.confirmations = self.tx['confirmations']
            self.block_height = self.height - self.confirmations + 1
            self.datetime = datetime.fromtimestamp(self.tx['time'])
        else:
            self.confirmations = 0
            self.block_height = False


class txid(znc.Module):
    description = "Get TXID information"
    rate_limit = 5 # seconds between calls
    last_call = datetime.fromtimestamp(0)

    def say(self, target, message):
        self.PutIRC('PRIVMSG {} :{}'.format(target, message))
        self.PutUser(':{} PRIVMSG {} :{}'.format(self.GetNetwork().GetIRCNick().GetNickMask(), target, message))

    def check_for_txid(self, message):
        matches = re.search(r'^(?!000)([a-zA-Z0-9]{64})$', message)
        if matches and (datetime.now() - txid.last_call).seconds > txid.rate_limit:
            txid.last_call = datetime.now()
            id = matches.group(1)
            try:
                tx = TX(id)
                response = "~ {} in, {} out | {} vB, {} W | {} BTC, {} sat/B, {} sat/W, {} BTC/kB".format(
                    tx.num_inputs,
                    tx.num_outputs,
                    tx.bytes,
                    tx.weight,
                    "{:.8f}".format(tx.fee * 0.00000001),
                    tx.fee_byte,
                    tx.fee_weight,
                    "{:.8f}".format(tx.fee_kb)
                )

                if tx.confirmations:
                    response += " | {} confirms since {}, {}".format(
                        tx.confirmations,
                        tx.block_height,
                        tx.datetime.isoformat('T')
                    )
                else:
                    response += ", UNCONFIRMED"
                    response += ", {}RBF".format("" if tx.rbf else "NON-")
            except (bitcoin.rpc.InvalidAddressOrKeyError, IndexError) as e:
                response = "~ I cannot find this TXID in my mempool."
            except:
                response = "~ an internal error occurred."
                self.PutModule(traceback.format_exc())
            return response

    def OnUserMsg(self, target, message):
        response = self.check_for_txid(message.s)
        if response:
            self.PutIRC('PRIVMSG {} :{}'.format(target, message.s))
            self.say(str(target), response)
            return znc.HALT

    def OnPrivMsg(self, target, message):
        response = self.check_for_txid(message.s)
        if response:
            self.PutUser(':{} PRIVMSG {} :{}'.format(str(target), self.GetNetwork().GetIRCNick().GetNickMask(),  message.s))
            self.say(str(target), response)
            return znc.HALT

    def OnChanMsg(self, user, channel, message):
        if str(channel) in allowed_channels:
            response = self.check_for_txid(message.s)
            if response:
                self.PutUser(':{} PRIVMSG {} :{}'.format(user, str(channel), message.s))
                self.say(str(channel), response)
                return znc.HALT
