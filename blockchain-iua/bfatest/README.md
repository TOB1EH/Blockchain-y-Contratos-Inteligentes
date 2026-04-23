# Configuración y lanzamiento de un nodo de la BFA

## Instalación de `geth`

Para interactuar con la BFA, nos conviene utilizar un cliente que dialogue con la mayor cantidad de nodos posibles. Por esa razón usaremos la versión 1.9.22

Para ello podemos utilizar el comando `go install`:

```bash
go install github.com/ethereum/go-ethereum/cmd/geth@v1.9.22
```

## Inicialización del nodo

Para inicializar el nodo, invocaremos el comando `geth init` pasándole como argumento el nombre de un archivo en formato JSON que tiene la información necesaria para construir el bloque 0 de la cadena. Utilizaremos el archivo `genesis.json` que se encuentra en este directorio.

Además, debemos indicarle con la opción `-datadir` el directorio donde se almacenarán los archivos del nodo. En este caso, hemos establecido que ese directorio se llamará `node`.

```bash
miguel@MP:~$ cd
miguel@MP:~$ cd blockchain-iua/bfatest/
miguel@MP:~/blockchain-iua/bfatest$ geth --datadir node init genesis.json
INFO [03-15|20:46:14.442] Maximum peer count                       ETH=50 LES=0 total=50
INFO [03-15|20:46:14.488] Set global gas cap                       cap=50,000,000
INFO [03-15|20:46:14.490] Allocated cache and file handles         database=/home/miguel/blockchain-iua/bfatest/node/geth/chaindata cache=16.00MiB handles=16
INFO [03-15|20:46:14.540] Opened ancient database                  database=/home/miguel/blockchain-iua/bfatest/node/geth/chaindata/ancient readonly=false
INFO [03-15|20:46:14.540] Writing custom genesis block 
INFO [03-15|20:46:14.541] Persisted trie from memory database      nodes=1 size=171.00B time="126.646µs" gcnodes=0 gcsize=0.00B gctime=0s livenodes=1 livesize=0.00B
INFO [03-15|20:46:14.543] Successfully wrote genesis state         database=chaindata hash=67e3e0..ca7d58
INFO [03-15|20:46:14.543] Allocated cache and file handles         database=/home/miguel/blockchain-iua/bfatest/node/geth/lightchaindata cache=16.00MiB handles=16
INFO [03-15|20:46:14.598] Opened ancient database                  database=/home/miguel/blockchain-iua/bfatest/node/geth/lightchaindata/ancient readonly=false
INFO [03-15|20:46:14.598] Writing custom genesis block 
INFO [03-15|20:46:14.600] Persisted trie from memory database      nodes=1 size=171.00B time="157.25µs"  gcnodes=0 gcsize=0.00B gctime=0s livenodes=1 livesize=0.00B
INFO [03-15|20:46:14.601] Successfully wrote genesis state         database=lightchaindata hash=67e3e0..ca7d58
```

El directorio `bfatest` tendrá ahora la siguiente estructura:

```verbatim
.
├── config.toml
├── genesis.json
└── node
    ├── geth
    │   ├── chaindata
    │   │   ├── 000001.log
    │   │   ├── ancient
    │   │   │   ├── bodies.0000.cdat
    │   │   │   ├── bodies.cidx
    │   │   │   ├── bodies.meta
    │   │   │   ├── diffs.0000.rdat
    │   │   │   ├── diffs.meta
    │   │   │   ├── diffs.ridx
    │   │   │   ├── FLOCK
    │   │   │   ├── hashes.0000.rdat
    │   │   │   ├── hashes.meta
    │   │   │   ├── hashes.ridx
    │   │   │   ├── headers.0000.cdat
    │   │   │   ├── headers.cidx
    │   │   │   ├── headers.meta
    │   │   │   ├── receipts.0000.cdat
    │   │   │   ├── receipts.cidx
    │   │   │   └── receipts.meta
    │   │   ├── CURRENT
    │   │   ├── LOCK
    │   │   ├── LOG
    │   │   └── MANIFEST-000000
    │   ├── lightchaindata
    │   │   ├── 000001.log
    │   │   ├── ancient
    │   │   │   ├── bodies.0000.cdat
    │   │   │   ├── bodies.cidx
    │   │   │   ├── bodies.meta
    │   │   │   ├── diffs.0000.rdat
    │   │   │   ├── diffs.meta
    │   │   │   ├── diffs.ridx
    │   │   │   ├── FLOCK
    │   │   │   ├── hashes.0000.rdat
    │   │   │   ├── hashes.meta
    │   │   │   ├── hashes.ridx
    │   │   │   ├── headers.0000.cdat
    │   │   │   ├── headers.cidx
    │   │   │   ├── headers.meta
    │   │   │   ├── receipts.0000.cdat
    │   │   │   ├── receipts.cidx
    │   │   │   └── receipts.meta
    │   │   ├── CURRENT
    │   │   ├── LOCK
    │   │   ├── LOG
    │   │   └── MANIFEST-000000
    │   ├── LOCK
    │   └── nodekey
    └── keystore
```

## Lanzamiento del nodo

Para ejecutar el cliente, debemos invocar nuevamente `geth` con el argumento `-datadir`, y pasarle el Id de la red (en el caso de la red de prueba de la BFA es 55555000000) con el argumento -networkid

```bash
miguel@MP:~/blockchain-iua/bfatest$ geth -datadir node -networkid 55555000000
```

Sin embargo, para hacer que se conecte más rapidamente con otros nodos (*peers*), le pasaremos una lista de *bootnodes*, y una lista estática de nodos iniciales con los cuales conectarse. Esos datos, al igual que el `networkid` se encuentran definidos en el archivo `config.toml` que se encuentra en el directorio `bfatest`.

```bash
miguel@MP:~/blockchain-iua/bfatest$ geth -datadir node -config config.toml
INFO [03-15|20:58:25.942] Starting Geth on Ethereum mainnet... 
INFO [03-15|20:58:25.943] Bumping default cache on mainnet         provided=1024 updated=4096
INFO [03-15|20:58:25.943] Maximum peer count                       ETH=50 LES=0 total=50
INFO [03-15|20:58:26.035] Set global gas cap                       cap=50,000,000
INFO [03-15|20:58:26.041] Allocated trie memory caches             clean=614.00MiB dirty=1024.00MiB
INFO [03-15|20:58:26.041] Allocated cache and file handles         database=/home/miguel/blockchain-iua/bfatest/node/geth/chaindata cache=2.00GiB handles=524,288
INFO [03-15|20:58:26.161] Opened ancient database                  database=/home/miguel/blockchain-iua/bfatest/node/geth/chaindata/ancient readonly=false
INFO [03-15|20:58:26.161]  
INFO [03-15|20:58:26.161] --------------------------------------------------------------------------------------------------------------------------------------------------------- 
INFO [03-15|20:58:26.161] Chain ID:  99118822 (unknown) 
INFO [03-15|20:58:26.162] Consensus: Clique (proof-of-authority) 
INFO [03-15|20:58:26.162]  
INFO [03-15|20:58:26.162] Pre-Merge hard forks: 
INFO [03-15|20:58:26.162]  - Homestead:                   0        (https://github.com/ethereum/execution-specs/blob/master/network-upgrades/mainnet-upgrades/homestead.md) 
INFO [03-15|20:58:26.162]  - Tangerine Whistle (EIP 150): 0        (https://github.com/ethereum/execution-specs/blob/master/network-upgrades/mainnet-upgrades/tangerine-whistle.md) 
INFO [03-15|20:58:26.162]  - Spurious Dragon/1 (EIP 155): 0        (https://github.com/ethereum/execution-specs/blob/master/network-upgrades/mainnet-upgrades/spurious-dragon.md) 
INFO [03-15|20:58:26.162]  - Spurious Dragon/2 (EIP 158): 0        (https://github.com/ethereum/execution-specs/blob/master/network-upgrades/mainnet-upgrades/spurious-dragon.md) 
INFO [03-15|20:58:26.162]  - Byzantium:                   4        (https://github.com/ethereum/execution-specs/blob/master/network-upgrades/mainnet-upgrades/byzantium.md) 
INFO [03-15|20:58:26.162]  - Constantinople:              <nil> (https://github.com/ethereum/execution-specs/blob/master/network-upgrades/mainnet-upgrades/constantinople.md) 
INFO [03-15|20:58:26.162]  - Petersburg:                  <nil> (https://github.com/ethereum/execution-specs/blob/master/network-upgrades/mainnet-upgrades/petersburg.md) 
INFO [03-15|20:58:26.162]  - Istanbul:                    <nil> (https://github.com/ethereum/execution-specs/blob/master/network-upgrades/mainnet-upgrades/istanbul.md) 
INFO [03-15|20:58:26.162]  - Berlin:                      <nil> (https://github.com/ethereum/execution-specs/blob/master/network-upgrades/mainnet-upgrades/berlin.md) 
INFO [03-15|20:58:26.162]  - London:                      <nil> (https://github.com/ethereum/execution-specs/blob/master/network-upgrades/mainnet-upgrades/london.md) 
INFO [03-15|20:58:26.162]  
INFO [03-15|20:58:26.162] The Merge is not yet available for this network! 
INFO [03-15|20:58:26.162]  - Hard-fork specification: https://github.com/ethereum/execution-specs/blob/master/network-upgrades/mainnet-upgrades/paris.md) 
INFO [03-15|20:58:26.162] --------------------------------------------------------------------------------------------------------------------------------------------------------- 
INFO [03-15|20:58:26.162]  
INFO [03-15|20:58:26.162] Initialising Ethereum protocol           network=55,555,000,000 dbversion=8
INFO [03-15|20:58:26.163] Loaded most recent local header          number=0 hash=67e3e0..ca7d58 td=1 age=3y10mo1w
INFO [03-15|20:58:26.163] Loaded most recent local full block      number=0 hash=67e3e0..ca7d58 td=1 age=3y10mo1w
INFO [03-15|20:58:26.163] Loaded most recent local fast block      number=0 hash=67e3e0..ca7d58 td=1 age=3y10mo1w
INFO [03-15|20:58:26.163] Loaded local transaction journal         transactions=0 dropped=0
INFO [03-15|20:58:26.163] Regenerated local transaction journal    transactions=0 accounts=0
INFO [03-15|20:58:26.163] Gasprice oracle is ignoring threshold set threshold=2
WARN [03-15|20:58:26.164] Engine API enabled                       protocol=eth
WARN [03-15|20:58:26.164] Engine API started but chain not configured for merge yet 
INFO [03-15|20:58:26.164] Starting peer-to-peer node               instance=Geth/v1.10.21-stable-67109427/linux-amd64/go1.18.4
INFO [03-15|20:58:26.186] New local node record                    seq=1,678,924,446,180 id=502c56c97db3cf25 ip=127.0.0.1 udp=30303 tcp=30303
INFO [03-15|20:58:26.187] Started P2P networking                   self=enode://e0418d4d72b75f26391143fe7abcd93545e9af4a1172f08954690d40f23ac969951fc7bc7b16ada72cb635ed397fd63e4a74a1d19b66cb2c32705316c1339736@127.0.0.1:30303
INFO [03-15|20:58:26.188] IPC endpoint opened                      url=/home/miguel/blockchain-iua/bfatest/node/geth.ipc
INFO [03-15|20:58:26.188] Loaded JWT secret file                   path=/home/miguel/blockchain-iua/bfatest/node/geth/jwtsecret crc32=0x7b7aedd6
INFO [03-15|20:58:26.188] WebSocket enabled                        url=ws://127.0.0.1:8551
INFO [03-15|20:58:26.188] HTTP server started                      endpoint=127.0.0.1:8551 auth=true prefix= cors=localhost vhosts=localhost
INFO [03-15|20:58:28.830] New local node record                    seq=1,678,924,446,181 id=502c56c97db3cf25 ip=152.169.252.27 udp=30303 tcp=30303
INFO [03-15|20:58:36.189] Block synchronisation started 
INFO [03-15|20:58:36.279] Looking for peers                        peercount=1 tried=108 static=2
INFO [03-15|20:58:37.160] Imported new block headers               count=192 elapsed=36.479ms number=192 hash=62ba4a..6ea4b1 age=3y10mo1w
INFO [03-15|20:58:37.161] Downloader queue stats                   receiptTasks=0 blockTasks=0 itemSize=650.00B throttle=8192
INFO [03-15|20:58:37.162] Wrote genesis to ancients 
INFO [03-15|20:58:37.194] Imported new block receipts              count=192 elapsed=32.842ms number=192 hash=62ba4a..6ea4b1 age=3y10mo1w size=64.60KiB
INFO [03-15|20:58:37.349] Imported new block headers               count=192 elapsed=21.012ms number=384 hash=ebfa8e..962793 age=3y10mo1w
INFO [03-15|20:58:37.370] Imported new block receipts              count=192 elapsed=19.149ms number=384 hash=ebfa8e..962793 age=3y10mo1w size=65.04KiB
INFO [03-15|20:58:37.390] Imported new block headers               count=192 elapsed=19.817ms number=576 hash=6d03ed..df7dde age=3y10mo1w
INFO [03-15|20:58:37.408] Imported new block receipts              count=192 elapsed=16.250ms number=576 hash=6d03ed..df7dde age=3y10mo1w size=65.29KiB
INFO [03-15|20:58:37.436] Imported new block headers               count=192 elapsed=21.456ms number=768 hash=8efb9c..6fec31 age=3y10mo1w
INFO [03-15|20:58:37.462] Imported new block receipts              count=192 elapsed=24.616ms number=768 hash=8efb9c..6fec31 age=3y10mo1w size=65.27KiB
INFO [03-15|20:58:37.470] Imported new block headers               count=192 elapsed=21.442ms number=960 hash=ec4bb0..552d80 age=3y10mo1w
INFO [03-15|20:58:37.489] Imported new block receipts              count=192 elapsed=17.986ms number=960 hash=ec4bb0..552d80 age=3y10mo1w size=65.27KiB
INFO [03-15|20:58:37.506] Imported new block headers               count=192 elapsed=20.279ms number=1152 hash=b4c447..6f9db3 age=3y10mo1w
```

El cliente arranca, y una vez que logra conectarse con al menos un *peer*, comienza a sincronizar y a armar su copia local de la cadena.

Podemos conectarnos al nodo y tener acceso a una consola *javascript* mediante el comando `geth attach`. En esta ocasión lo haremos utilizando el protocolo IPC, con el *socket unix* `node/geth.ipc`:

```bash
miguel@MP:~/blockchain-iua/bfatest$ geth attach node/geth.ipc
Welcome to the Geth JavaScript console!

instance: Geth/v1.10.21-stable-67109427/linux-amd64/go1.18.4
at block: 0 (Wed May 22 2019 09:40:01 GMT-0300 (-03))
 datadir: /home/miguel/blockchain-iua/bfatest/node
 modules: admin:1.0 clique:1.0 debug:1.0 engine:1.0 eth:1.0 miner:1.0 net:1.0 personal:1.0 rpc:1.0 txpool:1.0 web3:1.0

To exit, press ctrl-d or type exit
> eth.syncing
{
  currentBlock: 520004,
  healedBytecodeBytes: 0,
  healedBytecodes: 0,
  healedTrienodeBytes: 0,
  healedTrienodes: 0,
  healingBytecode: 0,
  healingTrienodes: 0,
  highestBlock: 19783962,
  startingBlock: 157503,
  syncedAccountBytes: 0,
  syncedAccounts: 0,
  syncedBytecodeBytes: 0,
  syncedBytecodes: 0,
  syncedStorage: 0,
  syncedStorageBytes: 0
}
> 
```

Obsérvese que en este momento tenemos *dos* instancias de `geth` en ejecución: una es el cliente conectado a la red, que se encuentra sincronizando. La otra es la que se conecta por IPC con la primera y nos brinda esta consola javascript:

```bash
miguel@MP:~/blockchain-iua/bfatest$ pgrep -ax geth
177324 geth -datadir node -config config.toml
177501 geth attach node/geth.ipc
```

En la consola podemos ver:

* La versión del cliente `geth`. En este caso se trata de la versión 1.10.21 (que no es la versión más actual).
* El número de bloque. En este caso figura 0 porque todavía no terminó de sincronizar.
* Una lista de módulos que tenemos disponibles, y que nos permiten obtener información y realizar acciones sobre el nodo: `admin`, `clique`, `debug`, `engine`, `eth`, `miner`, `net`, `personal`, `rpc`, `txpool` y `web3`.

Vemos por ejemplo que invocando `eth.syncing` nos da información sobre el estado de la sincronización: se llegó al bloque 520004, sobre un total de 19783962 existentes en la cadena al momento de hacer la consulta.

El módulo `personal` permite la creación y manejo de cuentas. Sin embargo, ha sido declarado obsoleto a partir de la versión 1.11.0 de `geth`. El mecanismo recomendado en la actualidad implica el uso de la aplicación `clef`, pero si uno desea habilitar el módulo puede hacerlo agregando la opción `-rpc.enabledeprecatedpersonal` al arrancar el nodo.
