# Configuración de nodos de una red *Ethereum*

Los nodos de una red *Ethereum* tienen distintos requerimientos según sea el *mecanismo de consenso* utilizado.
Cuando se utiliza *Proof-of-Work* (PoW), como fue el caso de la red principal hasta 2022, o *Proof-of-Authority* (PoA), se requiere la instalación de un único programa cliente. En cambio, cuando se usa *Proof-of-Stake*, como es el caso de la red principal en la actualidad, se requieren **dos** clientes: un *cliente de ejecución* y un *cliente de consenso*.

En nuestro caso trabajaremos con redes que usan prueba de autoridad, por lo que sólo necesitamos utilizar un cliente. Si bien existen distintas posibilidades, utilizaremos la implementación oficial escrita en lenguaje Go, llamada [`geth`](https://geth.ethereum.org).

Conectaremos un nodo a la red de prueba de la *Blockchain Federal Argentina* (BFA).

Loa pasos necesarios para instalar y conectar un nodo a una red son:

1. Instalar el cliente `geth`
2. Inicializar la cadena con el bloque *génesis* de la red que corresponda.
3. Lanzar el cliente para que sincronice con la red

## Instalación del cliente `geth`

Pueden encontrarse instrucciones para instalar `geth` en distintos sistemas operativos en <https://geth.ethereum.org/docs/getting-started/installing-geth>

En Ubuntu, por ejemplo, puede instalarse con la siguiente secuencia de instrucciones:

```bash
sudo add-apt-repository -y ppa:ethereum/ethereum
sudo apt update
sudo apt install ethereum
```

Esto instala `geth` y algunas herramientas adicionales. 

Sin embargo **no utilizaremos este método**, ya que para interactuar con la BFA nos conviene utilizar una versión que nos permita interactuar con la mayor cantidad posible de nodos, y en este momento la versión adecuada es la 1.9.22.

### Instalación mediante `go install`

`geth` está escrito en el lenguaje Go, por lo que también puede instalarse mediante `go install`. Para ello, es necesario tener instalado el compilador de Go. Puede instalarse siguiendo las instrucciones en <https://golang.org/doc/install>. 

Como queremos instalar una versión específica de `geth`, también nos conviene instalar una versión específica de `go`. Normalmente esto no es necesario, pero en la versión 1.23 de `go` se introdujeron unos cambios que hacen que la compilación de la versión 1.9.22 de `geth` produzca errores. Por lo tanto, tenemos que utilizar una versión anterior.

En el caso de Ubuntu, la forma más sencilla de instalar una versión específica es utilizando `snap`:

```bash
sudo snap install --channel 1.22/stable go --classic
```

Una vez que se haya instalado Go, puede instalarse la versión deseada de geth`geth` con el siguiente comando:

```bash
go install github.com/ethereum/go-ethereum/cmd/geth@v1.9.22
```

Si en realidad quisieramos instalar la última versión, deberíamos ejecutar:

```bash
go install github.com/ethereum/go-ethereum/cmd/geth@latest
```

`go install` descargará los paquetes necesarios y compilará el programa, dejando el ejecutable en el directorio `~/go/bin`. Para que el programa sea accesible desde cualquier directorio, es necesario agregar ese directorio al `PATH`. Esto puede hacerse agregando la siguiente línea al archivo `.bashrc`:

```bash
export PATH=~/go/bin:$PATH
```

## Estructura de directorios

`geth` requiere la existencia de un directorio en el que descargará la cadena y creará ciertos archivos necesarios para su ejecución. La ubicación de ese directorio es arbitraria, pero a los efectos de esta materia asumiremos la existencia de una estructura de directorios predefinida, y el uso de una máquina con Linux.

Es posible utilizar otra estructura, pero en ese caso deberán adaptarse las instrucciones a cada estructura particular.

La base de la estructura será un directorio llamado `blockchain-iua`, situado en el *home directory* del usuario.
En ese directorio existirán distintos subdirectorios, destinados a albergar los nodos de distintas redes. Por ejemplo, `bfatest` contendrá los archivos correspondietes a la red de prueba de la BFA.

En esos subdirectorios, a su vez, existirá un directorio llamado `node`, que tendrá los archivos propios del nodo.

La forma más sencilla de crear esta estructura consiste en copiar el directorio `blockchain-iua` de este repositorio en el *home directory*.

Una vez que se haya configurado el nodo, nos quedará una estructura similar a la siguiente:

```verbatim
~
└── blockchain-iua
    └── bfatest
        └── node
            ├── geth
            │   ├── chaindata
            │   │   └── ancient
            │   ├── lightchaindata
            │   │   └── ancient
            │   ├── nodes
            │   └── triecache
            └── keystore
```

## Configuración del nodo y ejecución del cliente

* Nodo de la BFA: Ver las instrucciones en el [README](bfatest/README.md) del directorio `bfatest`.
