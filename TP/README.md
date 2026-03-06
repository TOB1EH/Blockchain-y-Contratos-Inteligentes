# Trabajos prácticos

Este directorio contiene los trabajos prácticos de la materia Blockchain y Contratos Inteligentes.

En general, los prácticos se publicarán los días jueves, y deberán ser entregados a más tardar antes de la clase siguiente. La forma de entrega es publicarlos en el repositorio individual que ha sido asignado a cada estudiante.

## Indicaciones generales

Todos los prácticos deben estar autocontenidos. Se asume que en la máquina en la que se ejecutan se encuentran instalados:

* Python 3
* node/npm
* hardhat

### Dependencia de bibliotecas externas

Deberán especificarse en un archivo `README.md` los pasos necesarios para instalar las dependencias, salvo en los siguientes casos:

#### Proyectos en Javascript

Si existe un archivo `package.json`, se asume que las dependencias se instalarán con `npm install`.

#### Proyectos en Python

Si existe un archivo `requirements.txt`, se asume que las dependencias se instalarán con `pip install -r requirements.txt`.

### Control de versiones

* Ningún requerimiento externo debe estar versionado (por ejemplo, un directorio `node_modules`, o el directorio correspondiente a un _virtual environment_ de Python).
* Ningún artefacto producto del _build_ del proyecto debe estar versionado.

## Posible _workflow_

Si bien no es mandatorio, se describe aquí un posible _workflow_ para descarga de los enunciados y publicación de los prácticos resueltos. La idea básica es usar un único repositorio local con dos ramas (_branches_), una rama `master` que contiene todo el material de estudio y los trabajos prácticos, y otra rama que contiene los prácticos resueltos y que envía los mismos al repositorio personal.

La rama `master` será, a todos los efectos, de solo lectura, y se utilizará para obtener los materiales y los prácticos, pero no como rama de trabajo.

Todas las indicaciones que siguen se basan en el uso de `git` desde la línea de comandos y se asume el uso del protocolo `ssh`. Se deberán hacer las adaptaciones correspondientes para otros tipos de clientes `git` y para el uso del protocolo `https`.

### Clonado del repositorio

Si bien es probable que el repositorio ya ha sido clonado, si no es así se puede ejecutar, en un directorio local, el comando:

    host:~/repos/blockchain-iua$ git clone git@bitbucket.org:blockchain-iua/2026.git

Esto creará un directorio llamado `2026` que contiene el repositorio, y desde el cual realizaremos el resto de las operaciones. El nombre del directorio es irrelevante, y puede cambiarse si se lo desea.

### Agregado de otro remoto

Hasta este momento el repositorio tiene declarado un único remoto, que apunta al repositorio que hemos clonado, y que se llama `origin`. Agregaremos ahora otro remoto, que apunte a nuestro repositorio personal.

Si nuestro repositorio personal se llama `montes`, y queremos llamar a nuestro remoto `entregas` podemos agregarlo como remoto con el comando:

    host:~/repos/blockchain-iua/2026$ git remote add entregas git@bitbucket.org:blockchain-iua/montes.git

### Creación de una nueva rama para gestionar los prácticos a resolver y entregar

Supongamos que queremos que la nueva rama se llame `practicos`. Si bien no es estrictamente necesario, es conveniente que se trate de una rama vacía, y con una historia independiente de la rama `master`. Es decir, no haremos nunca un `merge` entre ambas ramas.

Para ello, podemos ejecutar:

    host:~/repos/blockchain-iua/2026$ git checkout --orphan practicos

Esto creará una nueva rama sin historia, y con los contenidos de la rama `master` agregados al área de _stage_ y listos para hacer un commit. Como no es esto lo que queremos, los borramos con el comando:

    host:~/repos/blockchain-iua/2026$ git rm -rf .

Esto nos deja con una rama vacía y sin historia.

### Sincronizar con los contenidos actuales del remoto

Como es posible que el remoto tenga algo (un archivo README.md, un archivo .gitignore) hacemos un `pull` inicial, especificando el remoto, el nombre de la rama en el remoto (`master`) y el nombre de la rama local (`practicos`):

    host:~/repos/blockchain-iua/2026$ git pull entregas master:practicos

### Actualizar la rama `master` para obtener los prácticos y el resto del material

Antes de copiar un práctico a la rama `practicos` para resolverlo, lo obtenemos en la rama `master`

    host:~/repos/blockchain-iua/2026$ git checkout master
    host:~/repos/blockchain-iua/2026$ git pull

### Copiar los prácticos a la rama de trabajo

Dijimos que no haremos `merge` entre ramas, por lo que obtendremos los prácticos mediante _checkouts_ selectivos. Por ejemplo, si queremos tener en la rama `practicos` el trabajo práctico 0, haremos:

    host:~/repos/blockchain-iua/2026$ git checkout practicos
    host:~/repos/blockchain-iua/2026$ git checkout master -- TP/0
    host:~/repos/blockchain-iua/2026$ git commit -m "Enunciado del práctico 0"

### Enviar el práctico al repositorio personal

Podemos hacer un `push` indicando el remoto, rama de origen y rama de destino:

    host:~/repos/blockchain-iua/2026$ git push entregas practicos:master

Si se desea configurar para que no sea necesario especificar estos datos, puede hacerse:

    host:~/repos/blockchain-iua/2026$ git branch --set-upstream-to=entregas/master practicos

Según como esté configurado el repositorio local, este comando puede fallar. Por ejemplo, si el atributo `push.default` es `simple`, no está permitido hacer un `push` a una rama remota de nombre distinto.

Para resolver este problema debemos cambiar la configuración a `upstream`

    host:~/repos/blockchain-iua/2026$ git config --local --add push.default upstream
