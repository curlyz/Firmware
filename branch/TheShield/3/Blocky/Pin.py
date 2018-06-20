def getPin(port):
	if port == 'A1': return None,22,34;
	elif port == 'A2':return None ,23,35;
	elif port == 'A3':return 32 ,16,32;
	elif port == 'A4':return 33 ,4,33;
	elif port == 'D1':return 27 ,19,None;
	elif port == 'D2':return 13 ,17,None;
	elif port == 'D3':return 14 ,18,None;
	elif port == 'D4':return 25 ,26,None;
	else :return None ,None,None;
