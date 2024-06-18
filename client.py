import pickle
# import random
from sklearn.model_selection import train_test_split

import socket

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization

from flowerclient import FlowerClient
from node import get_keys, start_server
from going_modular.security import apply_smpc, sum_shares


def save_nodes_chain(nodes):
    for node in nodes:
        node[0].blockchain.save_chain_in_file(node[0].id)


class Client:
    def __init__(self, id, host, port, batch_size, train, test, dp=False, type_ss="additif", threshold=3, m=3,
                 name_dataset="Airline Satisfaction", model_choice="simplenet", choice_loss="cross_entropy", epochs=3, num_classes=10):
        self.id = id
        self.host = host
        self.port = port

        self.epochs = epochs
        self.type_ss = type_ss
        self.threshold = threshold
        self.m = m
        self.list_shapes = None

        self.frag_weights = []
        self.sum_dataset_number = 0

        self.node = {}
        self.connections = {}

        private_key_path = f"keys/{id}_private_key.pem"
        public_key_path = f"keys/{id}_public_key.pem"

        self.get_keys(private_key_path, public_key_path)

        x_train, y_train = train
        x_test, y_test = test
        #x_train, y_train = [], []  # train
        #x_test, y_test = [], []  # test
        #[(x_train.append(train[i][0]), y_train.append(train[i][1])) for i in range(len(train))]
        #[(x_test.append(test[i][0]), y_test.append(test[i][1])) for i in range(len(test))]
        x_train, x_val, y_train, y_val = train_test_split(x_train, y_train, test_size=0.2, random_state=42,
                                                          stratify=y_train if name_dataset == "Airline Satisfaction" else None)

        self.flower_client = FlowerClient.client(
            x_train=x_train, 
            x_val=x_val, 
            x_test=x_test, 
            y_train=y_train, 
            y_val=y_val, 
            y_test=y_test,
            batch_size=batch_size,
            model_choice=model_choice,
            diff_privacy=dp, 
            delta=1 / (2 * len(x_train)),
            epsilon=0.5,
            max_grad_norm=1.2,
            name_dataset=name_dataset,
            choice_loss=choice_loss,
            num_classes=num_classes
            )

    def start_server(self):
        start_server(self.host, self.port, self.handle_message, self.id)

    def handle_message(self, client_socket):
        data_length_bytes = client_socket.recv(4)
        if not data_length_bytes:
            return  # No data received, possibly handle this case as an error or log it
        data_length = int.from_bytes(data_length_bytes, byteorder='big')

        # Now read exactly data_length bytes
        data = b''
        while len(data) < data_length:
            packet = client_socket.recv(data_length - len(data))
            if not packet:
                break  # Connection closed, handle this case if necessary
            data += packet

        if len(data) < data_length:
            # Log this situation as an error or handle it appropriately
            print("Data was truncated or connection was closed prematurely.")
            return
        
        message = pickle.loads(data)

        message_type = message.get("type")

        if message_type == "frag_weights":
            weights = pickle.loads(message.get("value"))
            self.frag_weights.append(weights)

        elif message_type == "global_model":
            weights = pickle.loads(message.get("value"))
            self.flower_client.set_parameters(weights)

        client_socket.close()

    def train(self):
        """
        Function to train the model
        :return:
        """
        old_params = self.flower_client.get_parameters({})
        res = old_params[:]
        for i in range(self.epochs):
            # why 3 iterations?
            res = self.flower_client.fit(res, {})[0]
            loss = self.flower_client.evaluate(res, {})[0]
            # with open('output.txt', 'a') as f:
            #     f.write(f"client {self.id}: {loss} \n")
        print(f"client {self.id}: {loss} \n")
        # Apply SMPC (warning : list_shapes is initialized only after the first training)
        encrypted_lists, self.list_shapes = apply_smpc(res, len(self.connections) + 1, self.type_ss, self.threshold)
        # we keep the last share of the secret for this client and send the others to the other clients
        self.frag_weights.append(encrypted_lists.pop())
        return encrypted_lists

    def send_frag_clients(self, frag_weights):
        """
        function to send the shares of the secret to the other clients
        :param frag_weights: list of shares of the secret (one share for each other client)
        """
        for i, (k, v) in enumerate(self.connections.items()):
            address = v.get('address')

            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.connect(('127.0.0.1', address))

            serialized_data = pickle.dumps(frag_weights[i])

            message = {"type": "frag_weights", "value": serialized_data}

            # print("message", message)
            serialized_message = pickle.dumps(message)

            # Send the length of the message first
            client_socket.send(len(serialized_message).to_bytes(4, byteorder='big'))
            client_socket.send(serialized_message)

            # close the socket after sending
            client_socket.close()

    def send_frag_node(self):
        address = self.node.get('address')

        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect(('127.0.0.1', address))

        serialized_data = pickle.dumps(self.sum_weights)  # The values summed on the client side and sent to the node.
        message = {"type": "frag_weights", "id": self.id, "value": serialized_data, "list_shapes": self.list_shapes}

        serialized_message = pickle.dumps(message)

        # Send the length of the message first
        client_socket.send(len(serialized_message).to_bytes(4, byteorder='big'))
        client_socket.send(serialized_message)

        # Close the socket after sending
        client_socket.close()

        self.frag_weights = []

    def reset_connections(self):
        self.connections = {}

    def add_connections(self, id, address):
        with open(f"keys/{id}_public_key.pem", 'rb') as f:
            public_key = serialization.load_pem_public_key(
                f.read(),
                backend=default_backend()
            )

        self.connections[id] = {"address": address, "public_key": public_key}

    def update_node_connection(self, id, address):
        with open(f"keys/{id}_public_key.pem", 'rb') as f:
            public_key = serialization.load_pem_public_key(
                f.read(),
                backend=default_backend()
            )

        self.node = {"address": address, "public_key": public_key}

    @property
    def sum_weights(self):
        return sum_shares(self.frag_weights, self.type_ss)

    def get_keys(self, private_key_path, public_key_path):
        self.private_key, self.public_key = get_keys(private_key_path, public_key_path)
