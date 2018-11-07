# passivemeasurement
aaa
## Server 端代码的使用方法
#### 1. 进入目录 PI-Measurement/, 执行 make 操作；  
#### 2. 进入目录 PI-Measurement/proto/demo_grpc/, 打开文件 app.cpp, 修改 含有IP 地址的字段，修改IP为本机地址；打开文件 pi_server_main.cpp, 修改含有IP地址的字段，改为本机IP地址；

#### 3. 进入目录 PI-Measurement/, 执行 make 操作；     
#### 4. 进入目录 PI-Measurement/proto/demo_grpc/, 打开终端1， 执行命令  
```shell
sudo ./pi_server_dummy
```
#### 打开终端2， 执行命令  
```shell
./controller -c simple_router.json
```
