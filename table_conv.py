import re
sum_num = 0
sumtime = 0
sip = ""
dip = ""
proto = ""
sp = ""
dp = ""
wuyuanzu = ""

def str10_str16(str10):
	str0x16 = hex(int(str10))
	str16 = str0x16[2:]
	if len(str16) == 1:
		str16 = '0'+str16
	return str16

def s10_16_port(str10):
	str0x16 = hex(int(str10))
	str16 = str0x16[2:]
	if len(str16) == 1:
		str16 = '000' + str16
	if len(str16) == 2:
		str16 = '00' + str16
	if len(str16) == 3:
		str16 = '0' + str16
	return str16

file = open("table_conv.txt")
while 1:
    line = file.readline()
    sip = ""
    dip = ""
    proto = ""
    sp = ""
    dp = ""
    if not line:
        break
    pass # do something 
    sum_num = 2*sumtime + 1
    sumtime += 1
    ll = re.split(' ',line)
    ll0 = ll[0].split('.',3)
    ll1 = ll[1].split('.',3)
    ll2 = ll[2].split('.',3)
    ll3 = ll[3].split('.',3)
    ll4 = ll[4].split('\n',3)
    for i in range(4):
    	sip = sip + str10_str16(ll0[i])
    for i in range(4):
    	dip = dip + str10_str16(ll1[i])
    proto = str10_str16(ll2[0])
    sp = s10_16_port(ll3[0])
    dp = s10_16_port(ll4[0])
    five_tup_hex = sip+dip+proto+sp+dp
    # print sum_num, five_tup_hex, s10_16_port(sum_num)
    print sumtime, five_tup_hex
    
