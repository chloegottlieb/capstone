import hashlib
import json
from time import time
from urllib.parse import urlparse
from uuid import uuid4

import base58
import multibase
import multihash as mh
from morphys import ensure_bytes, ensure_unicode
import multicodec

import requests
from flask import Flask, jsonify, request

import os
import sys

#this code is a modified version of the blockchain built out in part 1 to include methods for generating CIDs and simulate an IPFS system (waiting on code from non-blockchain group members to make that work)


class BaseCID(object): #this class establishes use of CID and creates a new CID object within the IPFS simulation
    __hash__ = object.__hash__
    def __init__(self, version, codec, multihash):
        #version (int) CID version (either 0 or 1)
        #codec (string) codec used for encoding the hash
        #multihash (string) the multihash
        self._version = version
        self._codec = codec
        self._multihash = ensure_bytes(multihash)

    @property
    def version(self):
        return self._version

    @property
    def codec(self):
        return self._codec

    @property
    def multihash(self):
        return self._multihash

    @property
    def buffer(self):
        raise NotImplementedError

    def encode(self, *args, **kwargs):
        raise NotImplementedError

    def __repr__(self):
        def truncate(s, length):
            return s[:length] + b'..' if len(s) > length else s
        truncate_length = 20
        return '{class_}(version={version}, codec={codec}, multihash={multihash})'.format(
            class_=self.__class__.__name__,
            version=self._version,
            codec=self._codec,
            multihash=truncate(self._multihash, truncate_length),
        )

    def __str__(self):
        return ensure_unicode(self.encode())

    def __eq__(self, other):
        return (self.version == other.version) and (self.codec == other.codec) and (self.multihash == other.multihash)

class CIDv0(BaseCID): #CID version 0 object
    CODEC = 'dag-pb'

    def __init__(self, multihash):
        super(CIDv0, self).__init__(0, self.CODEC, multihash)

    @property
    def buffer(self): #this is the raw representation that gets encoded and it returns the multihash
        return self.multihash

    def encode(self): #this is the base58-encoded buffer and returns the cid
        return ensure_bytes(base58.b58encode(self.buffer))

    def to_v1(self): #returns the equivalent in CIDv1 by returning cid.CIDv1 object
        return CIDv1(self.CODEC, self.multihash)

class CIDv1(BaseCID): #CID version 1 object
    def __init__(self, codec, multihash):
        super(CIDv1, self).__init__(1, codec, multihash)

    @property
    def buffer(self): #raw representation of the CID
        return b''.join([bytes([self.version]), multicodec.add_prefix(self.codec, self.multihash)])

    def encode(self, encoding='base58btc'): #Encoded version of the raw representation of the cid
        # encoding (string) is the encoding to use to encode the raw representation, should be supported by py-multibase
        return multibase.encode(encoding, self.buffer)

    def to_v0(self):  #returns the equivalent in CIDv1 by returning cid.CIDv1 object
        if self.codec != CIDv0.CODEC:
            raise ValueError('CIDv1 can only be converted for codec {}'.format(CIDv0.CODEC))

        return CIDv0(self.multihash)

def make_cid(*args): #Creates cid.CIDv0 or cid.CIDv1 object
    """
    The function works with these signatures:
            make_cid(<base58 encoded multihash CID>) -> CIDv0
            make_cid(<multihash CID>) -> CIDv0
            make_cid(<multibase encoded multihash CID>) -> CIDv1
            make_cid(<version>, <codec>, <multihash>) -> CIDv1
    """
    if len(args) == 1:
        data = args[0]
        if isinstance(data, str):
            return from_string(data)
        elif isinstance(data, bytes):
            return from_bytes(data)
        else:
            raise ValueError('invalid argument passed, expected: str or byte, found: {}'.format(type(data)))
    elif len(args) == 3:
        version, codec, multihash = args
        if version not in (0, 1):
            raise ValueError('version should be 0 or 1, {} was provided'.format(version))
        if not multicodec.is_codec(codec):
            raise ValueError('invalid codec {} provided, please check'.format(codec))
        if not (isinstance(multihash, str) or isinstance(multihash, bytes)):
            raise ValueError('invalid type for multihash provided, should be str or bytes')

        if version == 0:
            if codec != CIDv0.CODEC:
                raise ValueError('codec for version 0 can only be {}, found: {}'.format(CIDv0.CODEC, codec))
            return CIDv0(multihash)
        else:
            return CIDv1(codec, multihash)
    else:
        raise ValueError('invalid number of arguments, expected 1 or 3')

def is_cid(cidstr): #Checks if a given input string is valid encoded CID or not
    try:
        return bool(make_cid(cidstr))
    except ValueError:
        return False

def from_string(cidstr): #Creates a CID object from a encoded form
    cidbytes = ensure_bytes(cidstr, 'utf-8')
    return from_bytes(cidbytes)

def from_bytes(cidbytes): #Creates a CID object from a encoded form
#if the base58-encoded string is not a valid string or if the length of the argument is zero or if the length of decoded CID is invalid
    if len(cidbytes) < 2:
    	raise ValueError('argument length can not be zero')
    if cidbytes[0] != 0 and multibase.is_encoded(cidbytes):
        # if the bytestream is multibase encoded
        cid = multibase.decode(cidbytes)
        if len(cid) < 2:
            raise ValueError('cid length is invalid')
        data = cid[1:]
        version = int(cid[0])
        codec = multicodec.get_codec(data)
        multihash = multicodec.remove_prefix(data)
    elif cidbytes[0] in (0, 1):
        # if the bytestream is a CID
        version = cidbytes[0]
        data = cidbytes[1:]
        codec = multicodec.get_codec(data)
        multihash = multicodec.remove_prefix(data)
    else:
        # otherwise just base58-encoded multihash
        try:
            version = 0
            codec = CIDv0.CODEC
            multihash = base58.b58decode(cidbytes)
        except ValueError:
            raise ValueError('multihash is not a valid base58 encoded multihash')

    try:
        mh.decode(multihash)
    except ValueError:
        raise

    return make_cid(version, codec, multihash)


class Blockchain(object): # this class manages the chain by storing transactions and allowing new blocks to be added to the chain
	def __init__(self):
		self.chain = []
		self.current_cids = []
		self.new_block(previous_hash='1',proof=500) #genesis block
		self.new_cid = make_cid(version, codec, multihash)
        
    # new block is created to be added to the blockchain    
	def new_block(self, proof, previous_hash=None):
       
		block = {
			'index': len(self.chain) + 1,
			'timestamp': time(),
			'cids': self.current_cids,
			'proof': proof,
			'previous_hash': previous_hash or self.hash(self.chain[-1]),
		}

		self.current_cids = []
		self.chain.append(block)
		return block

	def new_cid_added(self, sender, recipient, new_cid):
		self.current_cids.append({
			'sender': sender,
			'recipient': recipient,
			'new_cid': new_cid,
		})
		return self.last_block['index'] + 1
	
	@staticmethod
	def hash(block):
		block_string = json.dumps(block, sort_keys=True).encode()
		return hashlib.sha256(block_string).hexdigest()


	@property
	def last_block(self): # function to return the block at the end of the chain
		return self.chain[-1]


	def proof_of_work(self, last_proof):
		proof = 0
		while self.valid_proof(last_proof, proof) is False:
			proof += 1

		return proof


	@staticmethod
	def valid_proof(last_proof, proof):
		guess = f'{last_proof}{proof}'.encode()
		guess_hash = hashlib.sha256(guess).hexdigest()
		return guess_hash[0] == "0"

	def valid_chain(self, chain):
		last_block = chain[0]
		current_index = 1

		while current_index < len(chain):
			block = chain[current_index]
			print(f'{last_block}')
			print(f'{block}')
			print("\n-----------\n")
            # Check that the hash of the block is correct
			if block['previous_hash'] != self.hash(last_block):
				return False

			# Check that the Proof of Work is correct
			if not self.valid_proof(last_block['proof'], block['proof']):
				return False

			last_block = block
			current_index += 1

		return True

	def resolve_conflicts(self):

		neighbours = self.nodes
		new_chain = None
# We're only looking for chains longer than ours
		max_length = len(self.chain)

# Grab and verify the chains from all the nodes in our network
		for node in neighbours:
			response = requests.get(f'http://{node}/chain')

		if response.status_code == 200:
			length = response.json()['length']
			chain = response.json()['chain']

				# Check if the length is longer and the chain is valid
			if length > max_length and self.valid_chain(chain):
				max_length = length
				new_chain = chain

		# Replace our chain if we discovered a new, valid chain longer than ours
		if new_chain:
			self.chain = new_chain
			return True

		return False

'''
API SETUP
'''

# Instantiate our Node
app = Flask(__name__)
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = False

# Generate a globally unique address for this node
node_identifier = str(uuid4()).replace('-', '')

# Instantiate the Blockchain
blockchain = Blockchain()


@app.route('/mine', methods=['GET'])
def mine():
    # We run the proof of work algorithm to get the next proof...
    last_block = blockchain.last_block
    last_proof = last_block['proof']
    proof = blockchain.proof_of_work(last_proof)


    ###HackerNoon outlines this part with giving a reward, can i do it the exact same way without adding a book id, ie just listing sender and recipient?
    # We must receive a reward for finding the proof.
    # The sender is "0" to signify that this node has mined a new coin.
    blockchain.new_cid_added(
        sender="0",
        recipient=node_identifier,
        new_cid=make_cid(version, codec, multihash)
        # amount=1,
    )

    # adding block to the chain
    previous_hash = blockchain.hash(last_block)
    block = blockchain.new_block(proof, previous_hash)

    response = {
        'message': "New Block Forged",
        'index': block['index'],
        'cids': block['cids'],
        'proof': block['proof'],
        'previous_hash': block['previous_hash'],
    }
    return jsonify(response), 200
  
@app.route('/cids/new', methods=['POST'])
def new_cid_added():
    return "add a new node"

@app.route('/chain', methods=['GET'])
def full_chain():
    response = {
        'chain': blockchain.chain,
        'length': len(blockchain.chain),
    }
    return jsonify(response), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)




@app.route('/cids/new', methods=['POST'])
def new_cid_added():
    values = request.get_json()

    # Check that the required fields are in the POST'ed data
    required = ['sender', 'recipient', 'new_cid']
    if not all(k in values for k in required):
        return 'Missing values', 400

    # Create a new cid
    index = blockchain.new_cid_added(values['sender'], values['recipient'], values['new_cid'])

    response = {'message': f'CID will be added to Block {index}'}
    return jsonify(response), 201

@app.route('/cids/register', methods=['POST'])
def register_nodes():
    values = request.get_json()

    nodes = values.get('nodes')
    if nodes is None:
        return "Error: Please supply a valid list of nodes", 400

    for node in nodes:
        blockchain.register_node(node)

    response = {
        'message': 'New nodes have been added',
        'total_nodes': list(blockchain.nodes),
    }
    return jsonify(response), 201


@app.route('/cids/resolve', methods=['GET'])
def consensus():
    replaced = blockchain.resolve_conflicts()

    if replaced:
        response = {
            'message': 'Our chain was replaced',
            'new_chain': blockchain.chain
        }
    else:
        response = {
            'message': 'Our chain is authoritative',
            'chain': blockchain.chain
        }

    return jsonify(response), 200




#Matthew (networking) code portion

# must be in directory with node.cpp executable

argc = len(sys.argv)
blocks = []
i = 1

while i < argc:
    blocks.append(argv[i])
    i += 1

os.system('./node 54000') # init user node (collects data)
for block in blocks:
    os.system('./node 54001 54000 move '+block) # collect each block

filename = input('Enter desired filename: ')
with open(filename, 'w') as outfile:
    for b in blocks:
        with open (b+'.txt') as infile:
            outfile.write(infile.read())
        outfile.write('\n')
    

	    