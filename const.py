#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import threading

USERNAME = 'ubuntu'  # username of servers
PASSWD = 'easonBACKPACK123'  # password of servers
MAXPAYLOAD = 4  # maximum number of containers running on one server 单个ip最大的容器数
NODE_COUNT = 40  # 主机个数 * MAXPAYLOAD   #所有节点数:最大为主机数×MAXPAYLOAD
IP_CONFIG = 'ip.txt'  # server IPs
SECONDS_IN_A_DAY = 60 * 60 * 24
SEMAPHORE = threading.BoundedSemaphore(15)
ABI = '[{"constant":false,"inputs":[{"name":"h0","type":"bytes32"},{"name":"cmtc","type":"bytes32"},{"name":"n","type":"uint256"}],"name":"Commit","outputs":[],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":false,"inputs":[{"name":"D","type":"uint256"},{"name":"cmts_a","type":"bytes32"}],"name":"Refund","outputs":[],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":false,"inputs":[{"name":"hi","type":"bytes32"},{"name":"L","type":"uint256"},{"name":"cmts_b","type":"bytes32"},{"name":"addressa","type":"address"}],"name":"Claim","outputs":[],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":true,"inputs":[{"name":"","type":"address"}],"name":"ev","outputs":[{"name":"cmts_A","type":"bytes32"},{"name":"cmts_B","type":"bytes32"},{"name":"cmtc","type":"bytes32"},{"name":"addressa","type":"address"},{"name":"N","type":"uint256"},{"name":"D","type":"uint256"},{"name":"H0","type":"bytes32"}],"payable":false,"stateMutability":"view","type":"function"},{"inputs":[],"payable":false,"stateMutability":"nonpayable","type":"constructor"}]'
BIN = '0x608060405234801561001057600080fd5b50610693806100206000396000f300608060405260043610610062576000357c0100000000000000000000000000000000000000000000000000000000900463ffffffff16806313c47e9514610067578063204b15dd146100b05780633e52507a146100eb578063cf61bde814610154575b600080fd5b34801561007357600080fd5b506100ae6004803603810190808035600019169060200190929190803560001916906020019092919080359060200190929190505050610221565b005b3480156100bc57600080fd5b506100e9600480360381019080803590602001909291908035600019169060200190929190505050610380565b005b3480156100f757600080fd5b506101526004803603810190808035600019169060200190929190803590602001909291908035600019169060200190929190803573ffffffffffffffffffffffffffffffffffffffff169060200190929190505050610418565b005b34801561016057600080fd5b50610195600480360381019080803573ffffffffffffffffffffffffffffffffffffffff169060200190929190505050610605565b604051808860001916600019168152602001876000191660001916815260200186600019166000191681526020018573ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff168152602001848152602001838152602001826000191660001916815260200197505050505050505060405180910390f35b336000803373ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff16815260200190815260200160002060030160006101000a81548173ffffffffffffffffffffffffffffffffffffffff021916908373ffffffffffffffffffffffffffffffffffffffff160217905550816000803373ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff1681526020019081526020016000206002018160001916905550806000803373ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff16815260200190815260200160002060040181905550826000803373ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff1681526020019081526020016000206006018160001916905550505050565b816000803373ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff16815260200190815260200160002060050154141561041457806000803373ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff16815260200190815260200160002060000181600019169055505b5050565b6000806000869150600090505b60c8811015610520576000808573ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff16815260200190815260200160002060060154600019168260001916141561048757809250610520565b816040516020018082600019166000191681526020019150506040516020818303038152906040526040518082805190602001908083835b6020831015156104e457805182526020820191506020810190506020830392506104bf565b6001836020036101000a038019825116818451168082178552505050505050905001915050604051809103902091508080600101915050610425565b858314156105fc57856000808673ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff16815260200190815260200160002060040154036000808673ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff16815260200190815260200160002060050181905550846000808673ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff16815260200190815260200160002060010181600019169055505b50505050505050565b60006020528060005260406000206000915090508060000154908060010154908060020154908060030160009054906101000a900473ffffffffffffffffffffffffffffffffffffffff169080600401549080600501549080600601549050875600a165627a7a723058200de63ddc8dc3dd8de1dd00766d638e04473d87ba7160c0123f97b065b201ea620029'


# CONFIG = 'testLatency2.txt'  # config file for HIBEChain
# USERNAME = 'dell'  # username of servers
# PASSWD = 'dell@2017'  # password of servers
# MAXPAYLOAD = 2  # maximum number of containers running on one server
# IP_CONFIG = 'ip.txt'  # server IPs
# SECONDS_IN_A_DAY = 60 * 60 * 24
# SEMAPHORE = threading.BoundedSemaphore(15)

# wait after copy... for 100 nodes
