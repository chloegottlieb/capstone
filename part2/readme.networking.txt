# readme.networking.txt
# Matthew Herdzik
# CSCI 499
# IPFS FINAL PROJECT
# version: FINAL
# contents: ['node.cpp','ipfs_hlpr.h']
# build: g++ node.cpp -o node
# execute: 
	reader: ./n <SOURCEPORT>
	sender: ./n <SOURECPORT> <DESTPORT> <FILEARG> <FILEHASH>
# FILEARG(s) = ['create', 'move', 'delete']
# sample: 
	./node 54000
	./node 54001 54000 move <FILEHASH>

# Note: In order to circumvent memory leak issues and reduce overhead, \
	downsized from last version of individual project {v5.2}, attached \
	as zip.

