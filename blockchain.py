from block import Block
import numpy as np 
import hashlib

class Blockchain:
    def __init__(self):
        self.blocks = []
        self.add_genesis_block()

    def add_block(self, block):
        self.blocks.append(block)    

    def is_valid_block(self, block, hash):
        loaded_weights_dict = np.load(block.storage_reference)
        loaded_weights = [loaded_weights_dict[f'param_{i}'] for i in range(len(loaded_weights_dict)-1)]
        loaded_weights = (loaded_weights, loaded_weights_dict[f'len_dataset'])

        hash_model = hashlib.sha256()
        hash_model.update(str(loaded_weights).encode('utf-8'))
        hash_model = hash_model.hexdigest()

        if block.cryptographic_hash == hash and block.calculated_hash == hash_model: 
            return True
        else: 
            return False

    def add_genesis_block(self):
        genesis_block = Block(0, "", "", "", "")
        self.blocks.append(genesis_block)
  
    @property
    def len_chain(self): 
        return len(self.blocks)

    def print_blockchain(self):
        # Print the contents of the blockchain
        for block in self.blocks:
            print(block)

    def save_chain_in_file(self, filename): 
        with open(f"{filename}.txt", "w") as f: 
            for block in self.blocks: 
                f.write("\n\n================ \n")
                f.write(f"prev_hash:\t\t {str(block.previous_block_cryptographic_hash)} \n")
                f.write(f"Data:\t\t {str(block.storage_reference)} {str(block.calculated_hash)} \n")
                f.write(f"Model type:\t\t {str(block.model_type)} \n")
                f.write(f"Number:\t\t {str(block.block_number)} \n")
                f.write(f"Hash:\t\t {str(block.cryptographic_hash)} \n")
                f.write("\n\n================ \n")