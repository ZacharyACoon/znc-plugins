import os, json
import znc

module_path = os.path.dirname(__file__)


class premessages(znc.Module):
    description = "Pre-recorded messages."
    cache = module_path + '/premessages.json'

    def __init__(self):
        self.messages = {}

    def OnLoad(self):
        if os.path.exists(premessages.cache):
            with open(premessages.cache, 'r') as f:
                self.messages = json.load(f)

    def OnUserMsg(self, target, message):
        if message.s in messages:
            response = messages[message.s]
            for line in response:
                self.PutIRC('PRIVMSG {} :{}'.format(target, line))
                self.PutUser(':{} PRIVMSG {} :{}'.format(self.GetNetwork().GetIRCNick().GetNickMask(), target, line))
            return znc.HALT
