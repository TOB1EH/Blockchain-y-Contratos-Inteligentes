# Trabajo práctico 3

## 1. Desplegar un nodo de la red de prueba de la BFA

Instale `geth`, tal como se describe en el [README](../../blockchain-iua/README.md) de la carpeta `blockchain-iua`, y despliegue un nodo de la red de prueba de la BFA, como se explica en el [README](../../blockchain-iua/bfatest/README.md) de la carpeta `bfatest`.

### Conexión con el nodo

Es posible conectarse con el nodo vía IPC o vía HTTP.

#### Vía IPC

```console
~$ geth attach blockchain-iua/bfatest/node/geth.ipc 
Welcome to the Geth JavaScript console!

instance: Geth/v1.10.16-stable-20356e57/linux-amd64/go1.17.5
at block: 0 (Wed May 22 2019 09:40:01 GMT-0300 (-03))
 datadir: /home/miguel/blockchain-iua/bfatest/node
 modules: admin:1.0 clique:1.0 debug:1.0 eth:1.0 miner:1.0 net:1.0 personal:1.0 rpc:1.0 txpool:1.0 web3:1.0

To exit, press ctrl-d or type exit
> 
```

#### Vía HTTP

```console
~$ geth attach http://localhost:8545
Welcome to the Geth JavaScript console!

instance: Geth/v1.10.16-stable-20356e57/linux-amd64/go1.17.5
at block: 0 (Wed May 22 2019 09:40:01 GMT-0300 (-03))
 modules: eth:1.0 net:1.0 rpc:1.0 web3:1.0

To exit, press ctrl-d or type exit
>  
```

Para que el nodo reciba conexiones via HTTP es necesario lanzarlo con el argumento `-http`.

## 2. Generar una cuenta

Genere una cuenta y publíquela en el *chat* grupal de la asignatura.
Recuerde que debe preservar el archivo con la clave privada para poder realizar transacciones con esa cuenta.

La cuenta puede crearse tanto desde la línea de comandos como desde la consola de `geth`.

### Creación de una cuenta desde la línea de comandos

```console
~$ geth --datadir blockchain-iua/bfatest/node/ account new
INFO [03-10|13:14:18.601] Maximum peer count                       ETH=50 LES=0 total=50
Your new account is locked with a password. Please give a password. Do not forget this password.
Password: 
Repeat password: 

Your new key was generated

Public address of the key:   0x1B523A926FbF8627973Aa26156151b313546b299
Path of the secret key file: blockchain-iua/bfatest/node/keystore/UTC--2022-03-10T16-14-25.035391903Z--1b523a926fbf8627973aa26156151b313546b299

- You can share your public address with anyone. Others need it to interact with you.
- You must NEVER share the secret key with anyone! The key controls access to your funds!
- You must BACKUP your key file! Without the key, it's impossible to access account funds!
- You must REMEMBER your password! Without the password, it's impossible to decrypt the key!

~$ 
```

## 3. Realizar una transacción

Después de haber enviado su dirección por correo electrónico, recibirá una transferencia de *ether* qué le permitirá realizar transacciones.

Envíe 1 `wei` a la dirección "0x5A5a966FeAA14e3018561314AA922f8e3A1E890d". Si la transacción es exitosa, debería recibir un nuevo monto de *ether*. Su saldo debería ser 100 *ether* menos el costo de la transacción realizada.

## 4. Desarrollo de *scripts* que interactúan con la red

Implemente las funcionalidades faltantes en los *scripts* `bfa_funds.py` y `show_transactions.py`, tal como se describe en los mismos.

La forma más sencilla de implementar estas funcionalidades es utilizando la biblioteca `web3.py`, que permite interactuar con un nodo de Ethereum desde Python. Para instalarla, es conveniente usar un entorno virtual de Python.

```console
~$ python3 -m venv web3py
~$ source web3py/bin/activate
(web3py) ~$ pip install web3
```

Puede encontrarse documentación sobre esta biblioteca en [https://web3py.readthedocs.io/](https://web3py.readthedocs.io/)
