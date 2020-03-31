#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from const import USERNAME, PASSWD, NODE_COUNT, IP_CONFIG, ABI, BIN
from gethnode import GethNode
from iplist import IPList
from conf import generate_genesis_pow
from functools import wraps
import time
import subprocess
import threading
from resultthread import MyThread
from web3 import Web3


class SingleChain():
    """
    Data structure for a set of Geth-pbft clients for a single blockchain.
    """
    def __init__(self, name, node_count, blockchain_id, ip_list, username=USERNAME, password=PASSWD):

        # Check if the input params are legal.
        if node_count > ip_list.get_full_count():
            raise ValueError("not enough IPs")

        self.username = username
        self.password = password
        self.chain_id = name    # chain id
        self.node_count = node_count
        self.blockchain_id = blockchain_id
        self.ip_list = ip_list
        self.nodes = []
        self.ips = set()
        self.if_set_number = False
        self.if_set_id = False
        self.is_terminal = False
        self.config_file = None
        self.accounts = []

    def singlechain_start(self):
        """Start all containers for a single chain."""
        threads = []
        for index in range(self.node_count):
            node_index = index + 1
            tmp = GethNode(self.ip_list, node_index, self.blockchain_id, self.username, self.password)
            self.ips.add(tmp.ip)
            self.nodes.append(tmp)
            # xq start a thread， target stand for a function that you want to run ,args stand for the parameters
            t = threading.Thread(target=tmp.start)
            t.start()
            threads.append(t)
            time.sleep(0.3)

        for t in threads:
            # xq threads must run the join function, because the resources of main thread is needed
            t.join()

        for index in range(self.node_count):
            print(index, self.nodes[index].accounts[0])
            self.accounts.append(self.nodes[index].accounts[0])
        print('The corresponding accounts are as follows:')
        print(self.accounts)

    def set_genesis(config):
        """Decorator for setting genesis.json file for a chain."""

        @wraps(config)
        def func(self, *args):
            config(self, *args)
            for server_ip in self.ips:
                #  将config_file远程发送到主机里
                subprocess.run(['sshpass -p %s scp %s %s@%s:%s' % (self.password, self.config_file,
                               self.username, server_ip.address, self.config_file)], stdout=subprocess.PIPE, shell=True)
                time.sleep(0.2)
                threads = []
                for node in self.nodes:
                    if node.ip == server_ip:
                        #  对于每个容器  将config_file 从主机copy到容器/root/目录下
                        command = 'docker cp %s %s:/root/%s' % (self.config_file, node.name, self.config_file)
                        t = threading.Thread(target=server_ip.exec_command, args=(command,))
                        t.start()
                        threads.append(t)
                        print('copying genesis file')
                        #  node._ifSetGenesis = True
                        time.sleep(0.1)
                for t in threads:
                    t.join()
            time.sleep(0.5)
        return func

    @set_genesis
    def config_consensus_chain(self):
        """Set genesis.json for a blockchain & init with genesis.json."""
        if self.chain_id is "":
            self.config_file = '0.json'
        else:
            self.config_file = '%s.json' % self.chain_id
        generate_genesis_pow(self.blockchain_id, self.accounts, self.config_file)
        time.sleep(0.02)

    def get_logs(self):
        for server_ip in self.ips:
            #  将log日志从容器复制到服务器主机里
            threads = []
            for node in self.nodes:
                if node.ip == server_ip:
                    #  对于每个容器  将log文件从到容器/root/目录下copy到主机
                    command = 'docker cp %s:/root/%s.log %s+%s.log' % (node.name, node.name, node.name, server_ip.address)
                    t = threading.Thread(target=server_ip.exec_command, args=(command,))
                    t.start()
                    threads.append(t)
                    print('copying log file')
                    time.sleep(0.1)
            for t in threads:
                t.join()
            time.sleep(0.2)
            subprocess.run(['sshpass -p %s scp %s@%s:%s %s' % (self.password, self.username, server_ip.address,
                                                               'evs-test85*', '/home/leaf/pycharm/src/testEvs/logs/')],
                           stdout=subprocess.PIPE, shell=True)

        time.sleep(0.5)

    @set_genesis
    def config_terminal(self):
        """Set genesis.json for terminal equipments."""
        if len(self.chain_id) == 4:
            self.config_file = '0.json'
        else:
            self.config_file = '%s.json' % self.chain_id[:-4]

    def get_chain_id(self):
        """return chain id of the chain."""
        return self.chain_id

    def get_primer_node(self):
        """Return the primer node of the set of Geth-pbft clients."""
        return self.nodes[0]

    def get_node_by_index(self, node_index):
        """Return the node of a given index."""
        if node_index <= 0 or node_index > len(self.nodes):
            raise ValueError("node index out of range")
        return self.nodes[node_index-1]

    def run_nodes(self):
        """Run nodes on a chain."""
        self.init_geth()
        self.run_geth_nodes()
        self.construct_chain()

    def init_geth(self):
        """
        run geth init command for nodes in a chain
        """
        print("self.config_file =", self.config_file)
        if self.config_file is None:
            raise ValueError("initID is not set")
        threads = []
        for server_ip in self.ips:
            for node in self.nodes:
                if node.ip == server_ip:
                    init_geth_command = 'docker exec -t %s geth --datadir abc init %s' % (node.name, self.config_file)
                    t = threading.Thread(target=server_ip.exec_command, args=(init_geth_command,))
                    t.start()
                    threads.append(t)
                    time.sleep(0.1)
        for t in threads:
            t.join()

    def run_geth_nodes(self):
        threads = []
        for node in self.nodes:
            start_geth_command = (
                                     'geth  --datadir abc --networkid 55661 --cache 2048 --port 30303 --rpcport 8545 --rpcapi '
                                     'admin,eth,miner,web3,net,personal,txpool,debug --rpc --rpcaddr 0.0.0.0 '
                                     '--unlock %s --password passfile --gasprice 0 --maxpeers 4096 --maxpendpeers 4096 --syncmode full --nodiscover  2>> %s.log') % (
                                     node.accounts[0], node.name)
            # print("start_geth_command------------", start_geth_command)
            command = 'docker exec -d %s bash -c \"%s\" ' % (node.name, start_geth_command)  # 主机内执行的完整命令
            print("docker_command------------", command)
            t = threading.Thread(target=node.ip.exec_command, args=(command,))  # 通过ip执行
            t.start()
            threads.append(t)
            time.sleep(0.5)
        for t in threads:
            t.join()
        print('node starting......')
        time.sleep(1)
        # must wait here
        for _ in range(3):
            print('.', end='')
            time.sleep(1)
        print()
        threads = []
        for node in self.nodes:
            t = threading.Thread(target=node.set_enode)  # 设置client的enode信息
            t.start()
            threads.append(t)
        for t in threads:
            t.join()
        print("---------------------set node---------------------")
        for node in self.nodes:
            node.set_enode()
        time.sleep(0.1)

    def construct_chain(self):
        """Construct a single chain.节点互联"""
        if not self.is_terminal:
            print("constructing single chain......")
            start_time = time.time()
            threads = []
            node_count = len(self.nodes)

            # connect nodes in a single chain with each other
            for i in range(node_count):  # (node_count)
                for j in range(i+1, node_count):  # (i+1,node_count)
                    print("---------------------add peer---------------------")
                    t1 = threading.Thread(target=self.nodes[i].add_peer, args=(self.nodes[j].enode,))
                    t1.start()
                    time.sleep(0.1)  # if fail. add this line.
                    threads.append(t1)
                # break
            for t in threads:
                t.join()
            print("-------------------------")
            print('active threads:', threading.active_count())
            end_time = time.time()
            print('active time:%.3fs' % (end_time - start_time))
            print("-------------------------")
            time.sleep(len(self.nodes) // 10)

    def destruct_chain(self):
        """Stop containers to destruct the chain."""
        threads = []
        for node in self.nodes:
            t = threading.Thread(target=node.stop)
            t.start()
            threads.append(t)
        for t in threads:
            t.join()

    def get_node_count(self):
        """Return the number of nodes of the blockchain."""
        return len(self.nodes)

    def start_miner(self):
        """Start miners of all nodes on the chain."""
        if not self.is_terminal:
            threads = []
            for node in self.nodes:
                t = threading.Thread(target=node.start_miner)
                t.start()
                threads.append(t)
                time.sleep(0.02)
            for t in threads:
                t.join()

# --------------------------------test-mul--------------------------------
# test_get_mul_contractaddr


def test_get_mul_contractaddr(contract_num, nodes):
    threads = []
    t1 = time.time()
    for i in range(contract_num):
        t = MyThread(nodes[i].get_contractaddr)
        threads.append(t)
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    t2 = time.time()
    test_get_mul_contractaddr_time = t2 - t1
    print("test_get_mul_contractaddr_time =", test_get_mul_contractaddr_time)
    contractaddr_list = []
    for t in threads:
        try:
            contractaddr = t.get_result()  # contractaddr为部署合约的地址
        except:
            contractaddr = "0x1"
        contractaddr_list.append(contractaddr)
    return contractaddr_list

# test_send_mul_mint


def test_send_mul_mint(mint_num, nodes, accounts, test_nodes):
    threads = []
    for i in range(mint_num):
        t = MyThread(nodes[i].send_mint_transaction, args=(accounts[i], "0x7d0", test_nodes[i]))
        threads.append(t)
        time.sleep(2)
    for t in threads:
        t.start()
        time.sleep(2)
    for t in threads:
        t.join()
    mint_exec_time = []
    mint_consensus_time = []
    mint_hash_list = []
    for t in threads:
        try:
            mint_hash, consensus_time, exec_time = t.get_result()  # consensus_time是从产生hash到打包到区块的时间
        except:
            mint_hash = "0x1"
            consensus_time = 0
        mint_hash_list.append(mint_hash)
        mint_consensus_time.append(consensus_time)
        mint_exec_time.append(exec_time)
    mint_consensus_totaltime = 0
    for i in range(mint_num):
        mint_consensus_totaltime += mint_consensus_time[i]
    mint_consensus_avetime = mint_consensus_totaltime/mint_num
    mint_exec_totaltime = 0
    for i in range(mint_num):
        mint_exec_totaltime += mint_exec_time[i]
    mint_exec_avetime = mint_exec_totaltime / mint_num
    return mint_hash_list, mint_consensus_avetime, mint_exec_avetime


# test_send_mul_convert

def test_send_mul_convert(convert_num, nodes, accounts, test_nodes):
    threads = []
    for i in range(convert_num):
        t = MyThread(nodes[i].send_convert_transaction, args=(accounts[i], test_nodes[i]))
        threads.append(t)
        time.sleep(2)
    for t in threads:
        t.start()
        time.sleep(2)
    for t in threads:
        t.join()
    convert_hash_list = []
    convert_start_time = []
    convert_end_time = []
    for t in threads:
        try:
            convert_hash, t1, t2 = t.get_result()  # consensus_time是从产生hash到打包到区块的时间
        except:
            convert_hash = "0x1"
            # t1 = 0
            # t2 = 0
        convert_hash_list.append(convert_hash)
        convert_start_time.append(t1)
        convert_end_time.append(t2)
        convert_start_time = sorted(convert_start_time, reverse=False)
        convert_end_time = sorted(convert_end_time, reverse=False)
    # convert_consensus_totaltime = 0
    # for i in range(convert_num):
    #     convert_consensus_totaltime += convert_consensus_time[i]
    # convert_consensus_avetime = convert_consensus_totaltime/convert_num
    # convert_exec_totaltime = 0
    # for i in range(convert_num):
    #     convert_exec_totaltime += convert_exec_time[i]
    # convert_exec_avetime = convert_exec_totaltime/convert_num
    return convert_hash_list, convert_start_time, convert_end_time


# test_send_mul_commit
def test_send_mul_commit(commit_num, nodes, accounts, contractaddr, test_nodes):
    threads = []
    for i in range(commit_num):
        t = MyThread(nodes[i].send_commit_transaction, args=(accounts[i], contractaddr, test_nodes[i]))
        threads.append(t)
        time.sleep(2)
    for t in threads:
        t.start()
        time.sleep(2)
    for t in threads:
        t.join()
    commit_hash_list = []
    commit_start_time = []
    commit_end_time = []
    for t in threads:
        try:
            commit_hash, t1, t2 = t.get_result()  # consensus_time是从产生hash到打包到区块的时间
        except:
            commit_hash = "0x1"
            consensus_time = 0
            exec_time = 0
        commit_hash_list.append(commit_hash)
        commit_start_time.append(t1)
        commit_end_time.append(t2)
        commit_start_time = sorted(commit_start_time, reverse=False)
        commit_end_time = sorted(commit_end_time, reverse=False)
    # commit_consensus_totaltime = 0
    # for i in range(commit_num):
    #     commit_consensus_totaltime += commit_consensus_time[i]
    # commit_consensus_avetime = commit_consensus_totaltime/commit_num
    # commit_exec_totaltime = 0
    # for i in range(commit_num):
    #     commit_exec_totaltime += commit_exec_time[i]
    # commit_exec_avetime = commit_exec_totaltime / commit_num
    return commit_hash_list, commit_start_time, commit_end_time


# test_send_mul_claim

def test_send_mul_claim(claim_num, nodes, accounts, contractaddr, addrA, test_nodes):
    threads = []
    for i in range(claim_num):
        t = MyThread(nodes[i].send_claim_transaction, args=(accounts[i], contractaddr, addrA[i], test_nodes[i]))
        threads.append(t)
        time.sleep(2)
    for t in threads:
        t.start()
        time.sleep(2)
    for t in threads:
        t.join()
    claim_hash_list = []
    claim_start_time = []
    claim_end_time = []
    for t in threads:
        try:
            claim_hash, t1, t2 = t.get_result()  # consensus_time是从产生hash到打包到区块的时间
        except:
            claim_hash = "0x1"
            # consensus_time = 0
            # exec_time = 0
        claim_hash_list.append(claim_hash)
        claim_start_time.append(t1)
        claim_end_time.append(t2)
        claim_start_time = sorted(claim_start_time, reverse=False)
        claim_end_time = sorted(claim_end_time, reverse=False)
    # claim_consensus_totaltime = 0
    # for i in range(claim_num):
    #     claim_consensus_totaltime += claim_consensus_time[i]
    # claim_consensus_avetime = claim_consensus_totaltime/claim_num
    # claim_exec_totaltime = 0
    # for i in range(claim_num):
    #     claim_exec_totaltime += claim_exec_time[i]
    # claim_exec_avetime = claim_exec_totaltime / claim_num
    return claim_hash_list, claim_start_time, claim_end_time


# test_send_mul_rerfund

def test_send_mul_refund(refund_num, nodes, accounts, contractaddr, test_nodes):
    threads = []
    for i in range(refund_num):
        t = MyThread(nodes[i].send_refund_transaction, args=(accounts[i], contractaddr, test_nodes[i]))
        threads.append(t)
        time.sleep(2)
    for t in threads:
        t.start()
        time.sleep(2)
    for t in threads:
        t.join()
    refund_hash_list = []
    refund_start_time = []
    refund_end_time = []
    for t in threads:
        try:
            refund_hash, t1, t2 = t.get_result()  # consensus_time是从产生hash到打包到区块的时间
        except:
            refund_hash = "0x1"
            # consensus_time = 0
            # exec_time = 0
        refund_hash_list.append(refund_hash)
        refund_start_time.append(t1)
        refund_end_time.append(t2)
        refund_start_time = sorted(refund_start_time, reverse=False)
        refund_end_time = sorted(refund_end_time, reverse=False)
    # refund_consensus_totaltime = 0
    # for i in range(refund_num):
    #     refund_consensus_totaltime += refund_consensus_time[i]
    # refund_consensus_avetime = refund_consensus_totaltime/refund_num
    # refund_exec_totaltime = 0
    # for i in range(refund_num):
    #     refund_exec_totaltime += refund_exec_time[i]
    # refund_exec_avetime = refund_exec_totaltime / refund_num
    return refund_hash_list, refund_start_time, refund_end_time


# test_send_mul_deposit

def test_send_mul_deposit(deposit_num, nodes, accounts, N, test_nodes):
    threads = []
    for i in range(deposit_num):
        t = MyThread(nodes[i].send_depositsg_transaction, args=(accounts[i], N, test_nodes[i]))
        threads.append(t)
        time.sleep(2)
    for t in threads:
        t.start()
        time.sleep(2)
    for t in threads:
        t.join()
    deposit_hash_list = []
    deposit_start_time = []
    deposit_end_time = []
    for t in threads:
        try:
            deposit_hash, t1, t2 = t.get_result()  # consensus_time是从产生hash到打包到区块的时间
        except:
            deposit_hash = "0x1"
            consensus_time = 0
            exec_time = 0
        deposit_hash_list.append(deposit_hash)
        deposit_start_time.append(t1)
        deposit_end_time.append(t2)
        deposit_start_time = sorted(deposit_start_time, reverse=False)
        deposit_end_time = sorted(deposit_end_time, reverse=False)
    # deposit_consensus_totaltime = 0
    # for i in range(deposit_num):
    #     deposit_consensus_totaltime += deposit_consensus_time[i]
    # deposit_consensus_avetime = deposit_consensus_totaltime/deposit_num
    # deposit_exec_totaltime = 0
    # for i in range(deposit_num):
    #     deposit_exec_totaltime += deposit_exec_time[i]
    # deposit_exec_avetime = deposit_exec_totaltime / deposit_num
    return deposit_hash_list, deposit_start_time, deposit_end_time


def test_node(nodesa , accountsa):
    """可用于测试节点是否工作 ， 除去不工作的节点"""
    threads = []
    node_count = len(nodesa)
    for i in range(node_count):
        t = MyThread(nodesa[i].get_peer_count)
        threads.append(t)
        time.sleep(2)
    for t in threads:
        t.start()
        time.sleep(2)
    for t in threads:
        t.join()
    tmp = 0
    for i, t in enumerate(threads):
        if(t.get_result() == None):
            nodesa[i] = 0
            accountsa[i] = 0
            # hash_list[i] = 0
            tmp += 1
            node_count -= 1

    for i in range(tmp):
        nodesa.remove(0)
        accountsa.remove(0)
        # hash_list.remove(0)

    print("----------------------alive_Node-------------------")
    print("nodesa = ", nodesa)
    print("accountsa = ", accountsa)
    # print("hash_list = ", hash_list)
    return node_count


# --------------------------------------------------------------------------------------------------------------------

def send_mul_redeem(redeem_num, nodes, accos, test_node):
    redeem_tran_time = []
    threads = []
    t1 = time.time()
    for i in range(redeem_num):
        t = MyThread(nodes[i].send_redeem_transaction, args=(accos[i], "0x10", test_node[i]))
        threads.append(t)
        time.sleep(2)
    for t in threads:
        t.start()
        time.sleep(2)
    for t in threads:
        t.join()
    t2 = time.time()
    print("redeem_time", t2 - t1)  # 30s
    redeem_hash_list = []
    for t in threads:
        try:
            redeem_hash, t_consen = t.get_result()
        except:
            redeem_hash = "0x1"
            t_consen = 0
        redeem_hash_list.append(redeem_hash)
        redeem_tran_time.append(t_consen)
    print(redeem_hash_list)
    print(redeem_tran_time)
    return redeem_hash_list, redeem_tran_time


def mul_miner_start(nodes):
    threads = []
    for i in range(len(nodes)):
        t = threading.Thread(nodes[i].start_miner())
        threads.append(t)
    for t in threads:
        t.start()
    for t in threads:
        t.join()


if __name__ == "__main__":
    ip_list = IPList(IP_CONFIG)
    ip_list.stop_all_containers()
    time.sleep(0.2)
    ip_list.remove_all_containers()
    c = SingleChain('evs-test', NODE_COUNT, 121, ip_list)
    c.singlechain_start() 
    c.config_consensus_chain() 
    c.run_nodes()

    #  全部节点用于挖矿
    for i in range(1, NODE_COUNT+1):
        c.get_node_by_index(i).start_miner()
    time.sleep(5)

    # 划分A类B类账户
    print("------------------账户列表------------------")
    accounts_A = []
    # accounts_B = []
    for i in range(1, NODE_COUNT+1):  # NODE_COUNT+1, 1
        accounts_A.append(c.get_node_by_index(i).get_accounts()[0])
    # for i in range(1, NODE_COUNT+1, 1):
    #     accounts_B.append(c.get_node_by_index(i).get_accounts()[0])
    print("A类账户：", accounts_A)
    # print("B类账户：", accounts_B)

    # 划分A类B类nodes
    print("------------------nodes列表------------------")
    nodes_A = []
    # nodes_B = []
    for i in range(1, NODE_COUNT+1):
        nodes_A.append(c.get_node_by_index(i))
    # for i in range(1, NODE_COUNT+1, 1):
    #     nodes_B.append(c.get_node_by_index(i))
    print("A类nodes：", nodes_A)
    # print("B类nodes：", nodes_B)

    print("-----------Wait for Generate DAG------------")
    print("Please wait for some minutes......")
    time.sleep(300)

    # Gen_hash_chain
    # print('------------------Gen_hash_chain------------------')
    # hashchainlength = 1000
    # t1 = time.time()
    # hashchainarr = c.get_node_by_index(1).Genhashchain(hashchainlength)
    # t2 = time.time()
    # Gen_hash_chain_time = t2 - t1
    # print("Gen_hash_chain_time =", Gen_hash_chain_time)
    # print("Hash_chain_Arr = ", hashchainarr)
    # time.sleep(3)

    # Get_contract_addr
    print('------------------Get-Contract-Address------------------')
    #  部署合约
    w3 = Web3(Web3.HTTPProvider("http://%s:%d" % (nodes_A[0].ip.address, nodes_A[0].rpc_port)))
    user = w3.eth.accounts[0]
    t1 = time.time()
    tx_hash = w3.eth.contract(abi=ABI, bytecode=BIN).constructor().transact({'from': user, 'gas': '0xc3500'})
    t2 = time.time()
    print("tx_hash =", tx_hash)
    depoly_contract_time = t2 - t1
    print("depoly_contract_time =", depoly_contract_time)
    tx_receipt = w3.eth.waitForTransactionReceipt(tx_hash, timeout=360)
    contract_address = tx_receipt['contractAddress']
    print("contract_address =", contract_address)

    # print('------------------test_send_mul_mint------------------')
    # mint_hash_list, mint_consensus_avetime, mint_exec_avetime = test_send_mul_mint(tran_number // 2, nodes_A,
    #                                                                                accounts_A, nodes_A)
    #
    # tran_number = get_mul_pubkey(tran_number, nodes_A, accounts_A, nodes_B, accounts_B, mint_hash_list)
    #
    # print("mint_hash_list = ", mint_hash_list)
    # print("mint_exec_avetime = ", mint_exec_avetime)
    # print("mint_consensus_avetime = ", mint_consensus_avetime)
    # print("Node_Count = ", tran_number)
    # time.sleep(2)
    # print("Please enter the command manually:")

    print('------------------test_send_mul_convert------------------')

    convert_hash_list, convert_start_list, convert_end_list = test_send_mul_convert(NODE_COUNT,
                                                                                               nodes_A, accounts_A,
                                                                                               nodes_A)

    print('-----------------print_info-----------------')
    # NODE_COUNT = test_node(nodes_A, accounts_A)
    # print("convert_hash_list = ", convert_hash_list)
    print("convert_start_list = ", convert_start_list)
    print("convert_end_list = ", convert_end_list)
    # print("convert_end_list = ", NODE_COUNT)
    time.sleep(2)
    convert_start_list = [str(i) for i in convert_start_list]
    convert_end_list = [str(i) for i in convert_end_list]

    with open('convert.txt', 'w') as f:
        f.write("=====convert_start=====" + '\n')
        for line in convert_start_list:
            f.write(line + '\n')
        f.write("=====convert_end=====" + '\n')
        for line in convert_end_list:
            f.write(line + '\n')
    print('convert成功写入文件......')

'''

    print('------------------test_send_mul_commit------------------')
    commit_hash_list, commit_start_list, commit_end_list = test_send_mul_commit(NODE_COUNT, nodes_A,
                                                                                           accounts_A,
                                                                                           contract_address,
                                                                                           nodes_A)
    print('-----------------print_info-----------------')
    # NODE_COUNT = test_node(nodes_A, accounts_A)
    # print("commit_hash_list = ", commit_hash_list)
    print("commit_start_list = ", commit_start_list)
    print("commit_end_list = ", commit_end_list)
    # print("Node_Count = ", NODE_COUNT)
    time.sleep(2)
    commit_start_list = [str(i) for i in commit_start_list]
    commit_end_list = [str(i) for i in commit_end_list]

    with open('commit.txt', 'w') as f:
        f.write("=====commit_start=====" + '\n')
        for line in commit_start_list:
            f.write(line + '\n')
        f.write("=====commit_end=====" + '\n')
        for line in commit_end_list:
            f.write(line + '\n')

    print('commit成功写入文件......')

    print('------------------test_send_mul_claim------------------')
    claim_hash_list, claim_start_list, claim_end_list = test_send_mul_claim(NODE_COUNT, nodes_A,
                                                                                       accounts_A, contract_address,
                                                                                       accounts_A, nodes_A)
    print('-----------------print_info-----------------')
    # NODE_COUNT = test_node(nodes_A, accounts_A)
    # print("claim_hash_list = ", claim_hash_list)
    print("claim_start_list = ", claim_start_list)
    print("claim_end_list = ", claim_end_list)
    # print("Node_Count = ", NODE_COUNT)
    time.sleep(2)
    claim_start_list = [str(i) for i in claim_start_list]
    claim_end_list = [str(i) for i in claim_end_list]

    with open('claim.txt', 'w') as f:
        f.write("=====claim_start=====" + '\n')
        for line in claim_start_list:
            f.write(line + '\n')
        f.write("=====claim_end=====" + '\n')
        for line in claim_end_list:
            f.write(line + '\n')

    print('claim成功写入文件......')

    print('------------------test_send_mul_refund------------------')
    refund_hash_list, refund_start_list, refund_end_list = test_send_mul_refund(NODE_COUNT, nodes_A,
                                                                                           accounts_A,
                                                                                           contract_address, nodes_A)
    print('-----------------print_info-----------------')
    # NODE_COUNT = test_node(nodes_A, accounts_A)
    # print("refund_hash_list = ", refund_hash_list)
    print("refund_start_list = ", refund_start_list)
    print("refund_end_list = ", refund_end_list)
    # print("Node_Count = ", NODE_COUNT)
    time.sleep(2)
    refund_start_list = [str(i) for i in refund_start_list]
    refund_end_list = [str(i) for i in refund_end_list]

    with open('refund.txt', 'w') as f:
        f.write("=====refund_start=====" + '\n')
        for line in refund_start_list:
            f.write(line + '\n')
        f.write("=====refund_end=====" + '\n')
        for line in refund_end_list:
            f.write(line + '\n')

    print('refund成功写入文件......')

    print('------------------test_send_mul_deposit------------------')
    deposit_hash_list, deposit_start_list, deposit_end_list = test_send_mul_deposit(NODE_COUNT,
                                                                                                 nodes_A, accounts_A,
                                                                                                 '0x0',
                                                                                                 nodes_A)
    print('-----------------print_info-----------------')
    # NODE_COUNT = test_node(nodes_A, accounts_A)
    # print("depositB_hash_list = ", deposit_hash_list)
    print("deposit_start_list = ", deposit_start_list)
    print("deposit_end_list = ", deposit_end_list)
    # print("Node_Count = ", NODE_COUNT)
    time.sleep(2)
    deposit_start_list = [str(i) for i in deposit_start_list]
    deposit_end_list = [str(i) for i in deposit_end_list]

    with open('deposit.txt', 'w') as f:
        f.write("=====deposit_start=====" + '\n')
        for line in deposit_start_list:
            f.write(line + '\n')
        f.write("=====deposit_end=====" + '\n')
        for line in deposit_end_list:
            f.write(line + '\n')

    print('deposit成功写入文件......')
    
'''

'''

    ##################################################################################################################
    ##################################################################################################################

    # print('------------------test_send_mul_depositA------------------')
    # deposit_hash_list, depositA_consensus_avetime, depositA_exec_avetime = test_send_mul_deposit(tran_number // 2,
    #                                                                                              nodes_A, accounts_A,
    #                                                                                              contractaddr_list,
    #                                                                                              refund_hash_list,
    #                                                                                              nodes_A)
    # tran_number = get_mul_pubkey(tran_number, nodes_A, accounts_A, nodes_B, accounts_B, contractaddr_list,
    #                              deposit_hash_list)
    # print("depositA_hash_list = ", deposit_hash_list)
    # print("depositA_exec_avetime = ", depositA_exec_avetime)
    # print("depositA_consensus_avetime = ", depositA_consensus_avetime)
    # print("Node_Count = ", tran_number)
    # time.sleep(2)

    with open('time.txt', 'w') as f:
        # f.write('Gen_hash_chain_time = %s\n' % Gen_hash_chain_time)
        # f.write('mint_exec_avetime = %s\n' % mint_exec_avetime)
        f.write('convert_exec_avetime = %s\n' % convert_exec_avetime)
        f.write('commit_exec_avetime = %s\n' % commit_exec_avetime)
        f.write('claim_exec_avetime = %s\n' % claim_exec_avetime)
        f.write('refund_exec_avetime = %s\n' % refund_exec_avetime)
        f.write('depositA_exec_avetime = %s\n' % deposit_exec_avetime)
        # f.write('depositB_exec_avetime = %s\n' % depositB_exec_avetime)
        f.write('========================================================\n')
        # f.write('mint_consensus_avetime = %s\n' % mint_consensus_avetime)
        f.write('convert_consensus_avetime = %s\n' % convert_consensus_avetime)
        f.write('commit_consensus_avetime = %s\n' % commit_consensus_avetime)
        f.write('claim_consensus_avetime = %s\n' % claim_consensus_avetime)
        f.write('refund_consensus_avetime = %s\n' % refund_consensus_avetime)
        f.write('depositA_consensus_avetime = %s\n' % deposit_consensus_avetime)
        # f.write('depositB_consensus_avetime = %s\n' % depositB_consensus_avetime)
        f.write('========================================================\n')

    for i in range(1, NODE_COUNT+1):
        c.get_node_by_index(i).stop_miner()
    time.sleep(10)

    c.get_logs()

    print("test-end.........")

'''

'''
    # 多节点串行测试
    #  Depoly_contract A(1,3,5,7,9......)
    contract_address_arr = [None] * (NODE_COUNT + 1)
    for i in range(1, NODE_COUNT, 2):
       print('------------------Get-Contract-Address------------------')
       #  取A类节点用于部署合约
       tmp_node = c.get_node_by_index(i)
       w3 = Web3(Web3.HTTPProvider("http://%s:%d" % (tmp_node.ip.address, tmp_node.rpc_port)))
       user = w3.eth.accounts[0]
       t1 = time.time()
       tx_hash = w3.eth.contract(abi=ABI, bytecode=BIN).constructor().transact({'from': user, 'gas': 2000000})
       t2 = time.time()
       depoly_contract_time = t2 - t1
       print("depoly_contract_time =", depoly_contract_time)
       tx_receipt = w3.eth.waitForTransactionReceipt(tx_hash, timeout=360)
       contract_address = tx_receipt['contractAddress']
       print("contract_address =", contract_address)
       contract_address_arr[i] = contract_address
    print("contract_address_arr = ", contract_address_arr)
    
    # Mint操作A(1,3,5,7,9......)
    for i in range(1, NODE_COUNT, 2):
        print('------------------Mint------------------')
        t1 = time.time()
        mint_hash = c.get_node_by_index(i).send_mint_transaction(c.get_node_by_index(i).get_accounts()[0], "0x100")
        t2 = time.time()
        mint_time = t2 - t1
        print("mint_time =", mint_time, "mint_hash =", mint_hash)
        mint_hash = mint_hash.split("\"")[1]
    time.sleep(70)

    # Convert操作A(1,3,5,7,9......)
    convert_hash_arr = [None] * (NODE_COUNT+1)
    convert_time_total = 0
    for i in range(1, NODE_COUNT, 2):
        print('------------------Convert------------------')
        t1 = time.time()
        convert_hash = c.get_node_by_index(i).send_convert_transaction(c.get_node_by_index(i).get_accounts()[0], "0x10")
        t2 = time.time()
        convert_time = t2 - t1
        convert_time_total += convert_time
        print("convert_time =", convert_time, "convert_hash =", convert_hash)
        convert_hash = convert_hash.split("\"")[1]
        convert_hash_arr[i] = convert_hash
    time.sleep(70)

    # Commit操作A(1,3,5,7,9......)
    commit_time_total = 0
    for i in range(1, NODE_COUNT, 2):
        print('------------------Commit------------------')
        t1 = time.time()
        commit_hash = c.get_node_by_index(i).send_commit_transaction(c.get_node_by_index(i).get_accounts()[0], "0x10",
                                                                     contract_address_arr[i],
                                                                     convert_hash_arr[i], hashchainarr[0], "0x10")
        t2 = time.time()
        commit_time = t2 - t1
        commit_time = t2 - t1
        commit_time_total += commit_time
        print("commit_time =", commit_time, "commit_hash =", commit_hash)
        commit_hash = commit_hash.split("\"")[1]
    time.sleep(70)

    # Claim操作B(2,4,6,8,10......)
    claim_time_total = 0
    claim_hash_arr = [None] * (NODE_COUNT+2)
    for i in range(2, NODE_COUNT+2, 2):
        print('------------------Claim------------------')
        t1 = time.time()
        claim_hash = c.get_node_by_index(i).send_claim_transaction(c.get_node_by_index(i).get_accounts()[0], "0x5",
                                                                   contract_address_arr[i-1], hashchainarr[5])
        t2 = time.time()
        claim_time = t2 - t1
        claim_time_total += claim_time
        print("claim_time =", claim_time, "claim_hash =", claim_hash)
        claim_hash = claim_hash.split("\"")[1]
        claim_hash_arr[i] = claim_hash
    time.sleep(70)

    # Refund操作A(1,3,5,7,9......)
    refund_time_total = 0
    refund_hash_arr = [None] * (NODE_COUNT + 1)
    for i in range(1, NODE_COUNT, 2):
        print('------------------Refund------------------')
        t1 = time.time()
        refund_hash = c.get_node_by_index(i).send_refund_transaction(c.get_node_by_index(i).get_accounts()[0], "0xb",
                                                                     contract_address_arr[i])
        t2 = time.time()
        refund_time = t2 - t1
        refund_time_total += refund_time
        print("refund_time =", refund_time, "refund_hash =", refund_hash)
        refund_hash = refund_hash.split("\"")[1]
        refund_hash_arr[i] = refund_hash
    time.sleep(70)

    # Deposit_sg_A
    for i in range(1, NODE_COUNT, 2):
        print('------------------Deposit_SG_A------------------')
        t1 = time.time()
        deposit_sgA_hash = c.get_node_by_index(i).send_depositsg_transaction(c.get_node_by_index(i).get_accounts()[0],
                                                                             contract_address_arr[i], refund_hash_arr[i])
        t2 = time.time()
        depositSGA_time = t2 - t1
        print("depositSGA_time =", depositSGA_time, "depositSGA_hash =", deposit_sgA_hash)
        deposit_sgA_hash = deposit_sgA_hash.split("\"")[1]
    time.sleep(70)

    # Deposit_sg_B
    for i in range(2, NODE_COUNT + 2, 2):
        print('------------------Deposit_SG_B------------------')
        t1 = time.time()
        deposit_sgB_hash = c.get_node_by_index(i).send_depositsg_transaction(c.get_node_by_index(i).get_accounts()[0],
                                                                             contract_address_arr[i-1], claim_hash_arr[i])
        t2 = time.time()
        depositSGB_time = t2 - t1
        print("depositSGB_time =", depositSGB_time, "depositSGB_hash =", deposit_sgB_hash)
        deposit_sgB_hash = deposit_sgB_hash.split("\"")[1]
    time.sleep(70)

    print("------------------Average_Time------------------")
    print("convert_time_ave =", convert_time_total/(NODE_COUNT/2))
    print("commit_time_ave =", commit_time_total/(NODE_COUNT/2))
    print("claim_time_ave =", claim_time_total/(NODE_COUNT/2))
    print("refund_time_ave =", refund_time_total/(NODE_COUNT/2))

#---------------------------------------------------------------------------------------------------------------------

    # 两个节点测试
    # 启动挖矿 账户1
    c.get_node_by_index(1).start_miner()
    time.sleep(20)

    # Depoly_contract
    print('------------------Get-Contract-Address------------------')
    w3 = Web3(Web3.HTTPProvider("http://101.76.211.197:8515"))
    user = w3.eth.accounts[0]
    t1 = time.time()
    tx_hash = w3.eth.contract(abi=ABI, bytecode=BIN).constructor().transact({'from': user, 'gas': 2000000})
    t2 = time.time()
    depoly_contract_time = t2 - t1
    print("depoly_contract_time =", depoly_contract_time)
    tx_receipt = w3.eth.waitForTransactionReceipt(tx_hash, timeout=360)
    contract_address = tx_receipt['contractAddress']
    print("contract_address = ", contract_address)
    
    # Gen_hash_chain
    print('------------------Gen_hash_chain------------------')
    hashchainlength = 1000
    t1 = time.time()
    hashchainarr = c.get_node_by_index(1).Genhashchain(hashchainlength)
    t2 = time.time()
    Gen_hash_chain_time = t2 - t1
    print("Gen_hash_chain_time =", Gen_hash_chain_time)
    print("Hash_chain_Arr = ", hashchainarr)
    time.sleep(10)

    # Mint操作
    print('------------------Mint------------------')
    t1 = time.time()
    mint_hash = c.get_node_by_index(1).send_mint_transaction(c.get_node_by_index(1).get_accounts()[0], "0x100")
    t2 = time.time()
    mint_time = t2 - t1
    print("mint_time =", mint_time, "mint_hash =", mint_hash)
    mint_hash = mint_hash.split("\"")[1]
    time.sleep(70)

    # Convert操作
    print('------------------Convert------------------')
    t1 = time.time()
    convert_hash = c.get_node_by_index(1).send_convert_transaction(c.get_node_by_index(1).get_accounts()[0], "0x10")
    t2 = time.time()
    convert_time = t2 - t1
    print("convert_time =", convert_time, "convert_hash =", convert_hash)
    convert_hash = convert_hash.split("\"")[1]
    time.sleep(70)

    # Commit操作
    print('------------------Commit------------------')
    t1 = time.time()
    commit_hash = c.get_node_by_index(1).send_commit_transaction(c.get_node_by_index(1).get_accounts()[0], "0x10",
                                                                 contract_address,
                                                                 convert_hash, hashchainarr[0], "0x10")
    t2 = time.time()
    commit_time = t2 - t1
    print("commit_time =", commit_time, "commit_hash =", commit_hash)
    commit_hash = commit_hash.split("\"")[1]
    time.sleep(70)

    # Claim操作
    print('------------------Claim------------------')
    t1 = time.time()
    claim_hash = c.get_node_by_index(2).send_claim_transaction(c.get_node_by_index(2).get_accounts()[0], "0x5",
                                                               contract_address, hashchainarr[5])
    t2 = time.time()
    claim_time = t2 - t1
    print("claim_time =", claim_time, "claim_hash =", claim_hash)
    claim_hash = claim_hash.split("\"")[1]
    time.sleep(70)

    # Refund操作
    print('------------------Refund------------------')
    t1 = time.time()
    refund_hash = c.get_node_by_index(1).send_refund_transaction(c.get_node_by_index(1).get_accounts()[0], "0xb",
                                                                 contract_address)
    t2 = time.time()
    refund_time = t2 - t1
    print("refund_time =", refund_time, "refund_hash =", refund_hash)
    refund_hash = refund_hash.split("\"")[1]
    time.sleep(70)

    # Deposit_sg_A
    print('------------------Deposit_SG_A------------------')
    t1 = time.time()
    deposit_sgA_hash = c.get_node_by_index(1).send_depositsg_transaction(c.get_node_by_index(1).get_accounts()[0],
                                                                         contract_address, refund_hash)
    t2 = time.time()
    depositSGA_time = t2 - t1
    print("depositSGA_time =", depositSGA_time, "depositSGA_hash =", deposit_sgA_hash)
    deposit_sgA_hash = deposit_sgA_hash.split("\"")[1]
    time.sleep(70)

    # Deposit_sg_B
    print('------------------Deposit_SG_B------------------')
    t1 = time.time()
    deposit_sgB_hash = c.get_node_by_index(2).send_depositsg_transaction(c.get_node_by_index(2).get_accounts()[0],
                                                                         contract_address, claim_hash)
    t2 = time.time()
    depositSGB_time = t2 - t1
    print("depositSGB_time =", depositSGB_time, "depositSGB_hash =", deposit_sgB_hash)
    deposit_sgB_hash = deposit_sgB_hash.split("\"")[1]
    time.sleep(70)

    # Redeem
    print("------------------Redeem_A------------------")
    t1 = time.time()
    redeem_hash = c.get_node_by_index(1).send_redeem_transaction(c.get_node_by_index(1).get_accounts()[0], "0x5")
    t2 = time.time()
    redeem_A_time = t2 - t1
    print("redeem_A_time =", redeem_A_time, "redeem_hash =", redeem_hash)
    time.sleep(70)

    # Redeem
    print("------------------Redeem_B------------------")
    t1 = time.time()
    redeem_hash = c.get_node_by_index(2).send_redeem_transaction(c.get_node_by_index(2).get_accounts()[0], "0x5")
    t2 = time.time()
    redeem_B_time = t2 - t1
    print("redeem_B_time =", redeem_B_time, "redeem_hash =", redeem_hash)
    time.sleep(70)

    # time
    print("------------------Time------------------")
    print("depoly_contract_time =", depoly_contract_time)
    print("Gen_hash_chain_time =", Gen_hash_chain_time)
    print("mint_time =", mint_time)
    print("convert_time =", convert_time)
    print("commit_time =", commit_time)
    print("claim_time =", claim_time)
    print("refund_time =", refund_time)
    print("depositSGA_time =", depositSGA_time)
    print("depositSGB_time =", depositSGB_time)
    print("redeem_A_time =", redeem_A_time)
    print("redeem_B_time =", redeem_B_time)

    # 停止挖矿
    c.get_node_by_index(1).stop_miner()
    c.destruct_chain()
    print("EVs-transact-success")
    
'''