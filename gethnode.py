# !/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import json
from iplist import IPList
from iplist import exec_command
from const import USERNAME, PASSWD, IP_CONFIG, SECONDS_IN_A_DAY, SEMAPHORE, ABI, BIN
from typing import Union, Optional, Any
import subprocess
import time
from web3 import Web3


class GethNode(object):
    """Data structure for Geth-pbft client."""
    def __init__(self, ip_list: IPList, node_index: int, blockchain_id: int,
                 username: str = USERNAME, password: str = PASSWD) -> None:
        self.id = node_index    # used in rpc call
        self.ip, self.rpc_port, self.ethereum_network_port = ip_list.get_new_port()
        self.node_index = node_index
        self.blockchain_id = blockchain_id
        self.name = 'evs-test' + str(self.rpc_port)    # docker container name of this node
        self._enode = ''
        self._accounts = []  # accounts list of a geth node
        self._headers = {'Content-Type': 'application/json', 'Connection': 'close'}    # for rpc call use
        self.username = username    # user name of login user of a server
        self.password = password    # password of login user of a server

    @property
    def enode(self) -> str:
        """Return enode information from admin.nodeInfo"""
        return self._enode

    @enode.setter
    def enode(self, enode_str: str) -> None:
        self._enode = enode_str

    @property
    def accounts(self) -> list:
        """Return a accounts list of a geth node"""
        return self._accounts

    def start(self) -> None:
        """Start a container for geth on remote server and create a new account."""
        # --ulimit nofile=<soft limit>:<hard limit> set the limit for open files
        docker_run_command = ('docker run --ulimit nofile=65535:65535 -td -p %d:8545 -p %d:30303 --rm --name %s '
                              'easonbackpack/evstest:latest' % (self.rpc_port, self.ethereum_network_port, self.name))
        time.sleep(0.6)
        result = self.ip.exec_command(docker_run_command)
        if result:
            if result.startswith('docker: Error'):
                print(result)
                print(self.ip)
                raise RuntimeError('An error occurs while starting docker container. Container maybe already exists')
            print('container of node %s of blockchain %s at %s:%s started' % (self.node_index, self.blockchain_id,
                                                                              self.ip.address, self.rpc_port))

        new_account_command = 'docker exec -t %s geth --datadir abc account new --password passfile' % self.name
        time.sleep(0.1)
        account = self.ip.exec_command(new_account_command).split()[-1][1:-1]
        time.sleep(0.3)
        if len(account) == 40:    # check if the account is valid
            self.accounts.append(account)

    def rpc_call(self, method: str, params: Optional[list] = None) -> Any:
        """Make a rpc call to this geth node."""
        if params is None:
            params = []
        data = json.dumps({    # json string used in HTTP requests
            'jsonrpc': '2.0',
            'method': method,
            'params': params,
            'id': self.id
        })
        url = "http://{}:{}".format(self.ip.address, self.rpc_port)
        with SEMAPHORE:
            with requests.Session() as r:
                response = r.post(url=url, data=data, headers=self._headers)
                content = json.loads(response.content.decode(encoding='utf-8'))
                print(content)
                result = content.get('result')
        err = content.get('error')
        if err:
            raise RuntimeError(err.get('message'))

        print('%s @%s : %s    %s' % (method, self.ip.address, self.rpc_port, result))
        return result

    def test(self, **kwargs):
        method = kwargs['method']
        params = kwargs['params']
        return self.rpc_call(method, params)

    def get_peer_count(self) -> int:
        """net.peerCount"""
        method = 'net_peerCount'
        time.sleep(0.02)
        result = self.rpc_call(method)
        return int(result, 16) if result else 0  # change hex number to dec

    def get_peers(self) -> str:
        """admin.peers"""
        method = 'admin_peers'
        peers = self.rpc_call(method)
        return peers

    def new_account(self, password: str = 'root') -> None:
        """personal.newAccount(password)"""
        method = 'personal_newAccount'
        params = [password]
        account = self.rpc_call(method, params)
        time.sleep(0.05)
        self.accounts.append(account[2:])

    def key_status(self) -> bool:
        """admin.key_status()"""
        method = 'admin_keyStatus'
        status = self.rpc_call(method)
        return status

    def unlock_account(self, account: str = '0', password: str = 'root', duration: int = SECONDS_IN_A_DAY) -> bool:
        """personal.unlockAccount()"""
        method = 'personal_unlockAccount'
        params = [account, password, duration]
        result = self.rpc_call(method, params)
        return result

    def get_pubkeyrlp(self, addr, pwd=""):
        """eth.getPubKeyRLP("0xeac93e13065db05706d7b60e29be532f350a3078","root") """
        params = [addr, pwd]
        method = 'eth_getPubKeyRLP'
        time.sleep(0.2)
        result = self.rpc_call(method, params)
        return result

    # EVs-Transactions #
    #############################################################################################
    def get_contractaddr(self):
        w3 = Web3(Web3.HTTPProvider("http://%s:%d" % (self.ip.address, self.rpc_port)))
        user = w3.eth.accounts[0]
        tx_hash = w3.eth.contract(abi=ABI, bytecode=BIN).constructor().transact({'from': user, 'gas': 2000000})
        tx_receipt = w3.eth.waitForTransactionReceipt(tx_hash, timeout=360)
        contract_address = tx_receipt['contractAddress']
        return contract_address

    def send_mint_transaction(self, ffrom, value, test_node):
        """eth.sendMintTransaction"""
        CMD = ("docker exec -t %s /usr/bin/geth attach ipc://root/abc/geth.ipc --exec \"eth.sendMintTransaction({from:\\\"%s\\\",value:\\\"%s\\\"})\"" % (self.name, ffrom, value))
        t3 = time.time()
        mint_hash = exec_command(CMD, self.ip)
        t4 = time.time()
        try:
            mint_hash = mint_hash.split("\"")[1]
            t1 = time.time()
            t2 = test_transaction(test_node, mint_hash)
        except:
            mint_hash = "0x1"
            t1 = 0
            t2 = 0
        return mint_hash, t2 - t1, t4 - t3

    def send_convert_transaction(self, ffrom, value, test_node):
        """eth.sendConvertTransaction"""
        CMD = ("docker exec -t %s /usr/bin/geth attach ipc://root/abc/geth.ipc --exec \"eth.sendConvertTransaction({from:\\\"%s\\\",value:\\\"%s\\\"})\"" % (self.name, ffrom, value))
        t3 = time.time()
        convert_hash = exec_command(CMD, self.ip)
        t4 = time.time()
        try:
            convert_hash = convert_hash.split("\"")[1]
            t1 = time.time()
            t2 = test_transaction(test_node, convert_hash)
        except:
            convert_hash = "0x1"
            t1 = 0
            t2 = 0
        return convert_hash, t2 - t1, t4 - t3

    def send_commit_transaction(self, ffrom, value, to, txhash, h0, N, test_node):
        """eth.sendCommitTransaction"""
        CMD = ("docker exec -t %s /usr/bin/geth attach ipc://root/abc/geth.ipc --exec \"eth.sendCommitTransaction({from:\\\"%s\\\",value:\\\"%s\\\",to:\\\"%s\\\",txhash:\\\"%s\\\",h0:\\\"%s\\\",N:\\\"%s\\\"})\"" % (self.name, ffrom, value, to, txhash, h0, N))
        t3 = time.time()
        commit_hash = exec_command(CMD, self.ip)
        t4 = time.time()
        try:
            commit_hash = commit_hash.split("\"")[1]
            t1 = time.time()
            t2 = test_transaction(test_node, commit_hash)
        except:
            commit_hash = "0x1"
            t1 = 0
            t2 = 0
        return commit_hash, t2 - t1, t4 - t3

    def send_claim_transaction(self, ffrom, value, to, hi, test_node):
        """eth.sendClaimTransaction"""
        CMD = ("docker exec -t %s /usr/bin/geth attach ipc://root/abc/geth.ipc --exec \"eth.sendClaimTransaction({from:\\\"%s\\\",value:\\\"%s\\\",to:\\\"%s\\\",hi:\\\"%s\\\"})\"" % (self.name, ffrom, value, to, hi))
        t3 = time.time()
        claim_hash = exec_command(CMD, self.ip)
        t4 = time.time()
        try:
            claim_hash = claim_hash.split("\"")[1]
            t1 = time.time()
            t2 = test_transaction(test_node, claim_hash)
        except:
            claim_hash = "0x1"
            t1 = 0
            t2 = 0
        return claim_hash, t2 - t1, t4 - t3

    def send_refund_transaction(self, ffrom, value, to, test_node):
        """eth.sendRefundTransaction"""
        CMD = ("docker exec -t %s /usr/bin/geth attach ipc://root/abc/geth.ipc --exec \"eth.sendRefundTransaction({from:\\\"%s\\\",value:\\\"%s\\\",to:\\\"%s\\\"})\"" % (self.name, ffrom, value, to))
        t3 = time.time()
        refund_hash = exec_command(CMD, self.ip)
        t4 = time.time()
        try:
            refund_hash = refund_hash.split("\"")[1]
            t1 = time.time()
            t2 = test_transaction(test_node, refund_hash)
        except:
            refund_hash = "0x1"
            t1 = 0
            t2 = 0
        return refund_hash, t2 - t1, t4 - t3

    def send_depositsg_transaction(self, ffrom, to, txhash, test_node):
        """eth.sendDepositsgTransaction"""
        CMD = ("docker exec -t %s /usr/bin/geth attach ipc://root/abc/geth.ipc --exec \"eth.sendDepositsgTransaction({from:\\\"%s\\\",to:\\\"%s\\\",txhash:\\\"%s\\\"})\"" % (self.name, ffrom, to, txhash))
        t3 = time.time()
        deposit_hash = exec_command(CMD, self.ip)
        t4 = time.time()
        try:
            deposit_hash = deposit_hash.split("\"")[1]
            t1 = time.time()
            t2 = test_transaction(test_node, deposit_hash)
        except:
            deposit_hash = "0x1"
            t1 = 0
            t2 = 0
        return deposit_hash, t2 - t1, t4 - t3


    def send_redeem_transaction(self, ffrom, value):
        """eth.sendRedeemTransaction"""
        CMD = ("docker exec -t %s /usr/bin/geth attach ipc://root/abc/geth.ipc --exec \"eth.sendRedeemTransaction({from:\\\"%s\\\",value:\\\"%s\\\"})\"" % (self.name, ffrom, value))
        return exec_command(CMD, self.ip)

    def Genhashchain(self, hashchainlength):
        """eth.genHashchain"""
        method = 'eth_genHashChain'
        params = [hashchainlength]
        return self.rpc_call(method, params)

    def get_transaction(self, transaction_id):
        """eth.getTransaction()"""
        method = 'eth_getTransaction'
        params = [transaction_id]
        return self.rpc_call(method, params)

    ###################################################################################################################

    #  G3
    def Get_Contract_Address(self, abi, ffrom, bin, gas):
        with open('contract.js', 'w') as contract:
            contract.write('mycon = eth.contract(%s);\n' % abi)
            contract.write('newcon = mycon.new({from:"%s",data:"%s",gas:%s});\n' % (ffrom, bin, gas))
            # contract.write('contractAddress = newcon.address;\n')
            # contract.write('console.log(newcon.transactionHash);\n')
            # contract.write('contractAddress = eth.getTransactionReceipt(newcon.transactionHash).contractAddress;\n')
            contract.write('eth.getTransactionReceipt(newcon.transactionHash);\n')
            # contract.write('console.log(contractAddress);\n')
        copy_cmd = 'sshpass -p %s scp contract.js %s@%s:contract.js' % (self.password, self.username,
                                                                               self.ip.address)
        subprocess.run(copy_cmd, stdout=subprocess.PIPE, shell=True)
        time.sleep(0.1)
        docker_cp_cmd = ("docker cp contract.js %s:/root/contract.js" % self.name)
        self.ip.exec_command(docker_cp_cmd)
        load_script_cmd = ("docker exec -t %s /usr/bin/geth attach ipc://root/abc/geth.ipc --exec 'loadScript(\"contract.js\")'" % self.name)
        return exec_command(load_script_cmd, self.ip)

    #  G2
    def GetTransactionReceipt_IPC(self, newcontransactionHash):
        """eth.getTransactionReceipt"""
        CMD = ("docker exec -t %s /usr/bin/geth attach ipc://root/abc/geth.ipc --exec \"eth.getTransactionReceipt(\\\"%s\\\").contractAddress\"" % (self.name, newcontransactionHash))
        return exec_command(CMD, self.ip)

    def GetTransactionReceipt_RPC(self, newHash):
        """eth.getTransactionReceipt"""
        method = 'eth_getTransactionReceipt'
        params = [newHash]
        return self.rpc_call(method, params)

    #  G1
    def contract(self, abi, ffrom, bin, gas):
        """eth.contract"""
        CMD = ("docker exec -t %s /usr/bin/geth attach ipc://root/abc/geth.ipc --exec \"mycon = eth.contract(\\\"%s\\\");mycon.new({from:\\\"%s\\\",bin:\\\"%s\\\",gas:\\\"%s\\\"})\"" % (self.name, abi, ffrom, bin, gas))
        return exec_command(CMD, self.ip)

    def contract_new(self, ffrom, bin, gas):
        """contract_new"""
        CMD = ("docker exec -t %s /usr/bin/geth attach ipc://root/abc/geth.ipc --exec \"mycon.new({from:\\\"%s\\\",bin:\\\"%s\\\",gas:\\\"%s\\\"})\"" % (self.name, ffrom, bin, gas))
        return exec_command(CMD, self.ip)

    ##################################################################################################

    def get_accounts(self):
        """eth.accounts"""
        method = 'eth_accounts'
        return self.rpc_call(method)

    def get_balance(self, account):
        """eth.getBalance()"""
        if not account.startswith('0x'):
            account = '0x' + account
        method = 'eth_getBalance'
        params = [account, 'latest']
        return self.rpc_call(method, params)

    def get_block_transaction_count(self, index):
        """eth.getBlockTransactionCount()"""
        method = 'eth_getBlockTransactionCountByNumber'
        params = [hex(index)]
        result = self.rpc_call(method, params)
        return int(result, 16) if result else 0  # change hex number to dec

    def remove_transaction(self) -> bool:
        """eth.removeTx()"""
        method = 'eth_removeTx'
        return self.rpc_call(method)

    def add_peer(self, *args) -> bool:
        """admin.addPeer()"""
        method = 'admin_addPeer'
        params = list(args)
        # sleep(0.01)
        result = self.rpc_call(method, params)
        return result

    # if RPC does not work well, use this method
    # IPC method can be a substitution for RPC method
    def ipc_add_peer(self, *args):
        """IPC version admin.addPeer()"""
        try:
            add_peer_command = ("docker exec -t %s geth attach ipc://root/abc/geth.ipc "
                                "--exec \"admin.addPeer%s\"" % (self.name, args))
            self.ip.exec_command(add_peer_command)
        except Exception as e:
            raise RuntimeError('%s:%s %s %s' % (self.ip, self.ethereum_network_port, self.rpc_port, e))

    def set_enode(self) -> None:
        """Set enode info of a node."""
        method = 'admin_nodeInfo'
        result = self.rpc_call(method)  # result from rpc call
        enode = result['enode'].split('@')[0]
        self.enode = '{}@{}:{}'.format(enode, self.ip.address, self.ethereum_network_port)

    def set_number(self, node_count: int, thresh: int) -> bool:
        """admin.set_number()"""
        # Check if the input params are legal
        if node_count < thresh:
            raise ValueError('nodeCount should be no less than threshold value')
        if thresh <= 0 or node_count <= 0:
            raise ValueError('nodeCount and threshold value should be positive')

        method = 'admin_setNumber'
        params = [node_count, thresh]
        time.sleep(0.1)
        return self.rpc_call(method, params)

    def set_level(self, level, max_level) -> bool:
        """admin.setLevel()"""
        # Check if the input params are legal
        if max_level < level:
            raise ValueError('level should be no larger than maxLevel')
        if level < 0:
            raise ValueError('level shoud be non-negative')

        method = 'admin_setLevel'
        params = [max_level, level]
        time.sleep(0.1)
        return self.rpc_call(method, params)

    def set_id(self, chain_id):
        """admin.setID()"""
        method = 'admin_setID'
        params = [chain_id]
        print('id is:', chain_id)
        # sleep(0.1)
        return self.rpc_call(method, params)

    def key_count(self):
        """eth.keyCount()"""
        method = 'eth_keyCount'
        return self.rpc_call(method)

    def txpool_status(self) -> int:
        """txpool.status"""
        method = 'txpool_status'
        result = self.rpc_call(method)
        time.sleep(0.1)
        print("txpool.status pending:%d, queued:%d" % (int(result['pending'], 16),
                                                       int(result['queued'], 16)))
        return int(result['pending'], 16) + int(result['queued'], 16)

    def start_miner(self) -> None:
        """miner.start()"""
        method = 'miner_start'
        return self.rpc_call(method)

    def stop_miner(self) -> None:
        """miner.stop()"""
        method = 'miner_stop'
        return self.rpc_call(method)

    def get_transaction_by_block_number_and_index(self, block_number, index) -> str:

        block_number_hex_string = hex(block_number)
        index_hex_string = hex(index)
        method = 'eth_getTransactionByBlockNumberAndIndex'
        params = [block_number_hex_string, index_hex_string]
        result = self.rpc_call(method, params)  # result from rpc call
        return result['hash'] if result else None

    def get_transaction_proof_by_hash(self, transaction_hash) -> list:
        """eth.getTxProofByHash()"""
        method = 'eth_getTxProofByHash'
        params = [transaction_hash]
        result = self.rpc_call(method, params)
        print(result)
        return result

    def get_transaction_proof_by_proof(self, transaction_proof: list) -> list:
        """eth.getTxProofByProf()"""
        method = 'eth_getTxProofByProof'
        params = [transaction_proof]
        result = self.rpc_call(method, params)
        print(result)
        return result

    def is_geth_running(self) -> bool:
        """Check if the client is running."""
        command = 'docker exec -t %s geth attach ipc://root/abc/geth.ipc --exec "admin.nodeInfo"' % self.name
        result = self.ip.exec_command(command)
        return False if result.split(':')[0] == 'Fatal' else True

    def stop(self) -> None:
        """Remove the geth-pbft node container on remote server."""
        stop_command = "docker stop %s" % self.name
        self.ip.exec_command(stop_command)
        print('node %s of blockchain %s at %s:%s stopped' % (self.node_index, self.blockchain_id,
                                                                 self.ip.address, self.rpc_port))


# 判断交易是否被共识
def test_transaction(node, tran):
    t_b = time.time()
    while True:
        if node.GetTransactionReceipt_RPC(tran) != None:
            tran_info = node.GetTransactionReceipt_RPC(tran)
            if tran_info['blockNumber'] !=  None:
                return time.time()
        t_e = time.time()
        if t_e-t_b > 500:
            return 0
        time.sleep(2)


if __name__ == "__main__":
    a = IPList(IP_CONFIG)
    a.stop_all_containers()
    time.sleep(0.2)
    a.remove_all_containers()
    n1 = GethNode(a, 1, 121)  # GethNode后实例化后的对象n
    n2 = GethNode(a, 2, 121)
    n1.start()
    n2.start()
    print(n1.accounts)
    print(n2.accounts)
    n1.stop()
    n2.stop()
    print("Gethnode successfully!")
