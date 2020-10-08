### 一、配置环境

#### 1、安装python3.7（如果已经有py3.7环境可略过自步骤）

查看版本： `python3 --version`

1、使用wget下载安装包
```
wget https://www.python.org/ftp/python/3.7.1/Python-3.7.1rc2.tgz
```
> 这个地址可以在：`https://www.python.org/downloads/source/`找到对应的版本。

2、解压该压缩文件: `tar zxvf Python-3.7.1rc2.tgz`

3、进去py这个目录，并编译安装
```
cd Python-3.7.1rc2
./configure
make
make install
```
编译问题参考[No module named '_ctypes'](https://blog.csdn.net/wang725/article/details/79905612)

4、创建软连接
```
rm -rf /usr/bin/python3
rm -rf /usr/bin/pip3
ln -s /usr/local/python3/bin/python3.7 /usr/bin/python3
ln -s /usr/local/python3/bin/pip3.7 /usr/bin/pip3
```

参考[升级文档](https://www.cnblogs.com/wongyi/p/9824236.html)

#### 2、安装其他环境依赖

```
sudo pip3 requests paramiko
sudo apt-get install openssh-server sshpass
```
安装问题参考[error](https://blog.csdn.net/zxd675816777/article/details/39119767)

#### 3、安装docker
1、安装
```sh
sudo apt-get update
sudo apt-get install apt-transport-https ca-certificates
sudo apt-get install docker.io
````
可参考[官方指南](https://docs.docker.com/install/linux/docker-ce/ubuntu/)

2、添加docker用户组
```sh
sudo groupadd docker             #添加docker用户组
sudo gpasswd -a $USER docker     #将登陆用户加入到docker用户组中
newgrp docker                    #更新用户组
docker ps                        #测试docker命令是否可以使用sudo正常使用

```

3、通过Dockerfile生成镜像
```
dockertest里面包括lib（.so文件），prfkey等文件，geth客户端，以及json文件
进入Dockerfile所在目录
docker build -t easonbackpack/evs512:latest .  在本地生成镜像，其中easonbackpack为你的dockerhub账号，evs512为你的镜像名称 
docker push easonbackpack/evs512:latest    上传到dockerhub官方仓库
```

4、获取docker镜像
```
docker pull easonbackpack/evs512:latest

docker配置结束   
docker images  查看镜像
docker ps 查看运行容器
docker ps -a  查看所有容器
docker rm containerid 删除容器
docker rmi imageid 删除镜像
```

### 二、文件介绍
* ip.txt  存放多主机ip地址
* const.py  ssh使用需要的用户名和密码以及其他变量
* conf.py   产生pow或者poa json文件
* iplist.py   对ip的处理，端口的一些分配，rpc端口和以太坊监听端口
* gethnode.py   单个节点的操作，通过rpc执行的addpeer等，通过ipc执行的send、Mint、update等函数操作
* singlechain.py   整条链的节点启动、连接、测试等所有的操作都是在该文件内
* localtest.py   用于本地rpc、ipc脚本测试


### 三、运行脚本

1、执行：
```
python3 iplist.py && python3 singlechain.py
```
如果报` No such file or directory: '/home/ethtest/.ssh/known_hosts'`，根据目录创建一个空文件即可。