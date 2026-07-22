const { pathToFileURL } = require("url");

/**
 * Despliega el contrato CFPFactory en la red especificada en Hardhat.
 */
async function main() {
    // Importar el entorno de Hardhat de manera dinámica para acceder a sus funcionalidades.
    const hardhatPath = require.resolve("hardhat", { paths: [process.cwd()] });
    const { default: hre } = await import(pathToFileURL(hardhatPath).href);

    // Obtener el objeto ethers del entorno de Hardhat
    const { ethers } = await hre.network.getOrCreate();

    // Crear una instancia del contrato CFPFactory y desplegarlo
    const CFPFactory = await ethers.getContractFactory("CFPFactory");

    // Desplegar el contrato y esperar a que se confirme la transacción
    // de despliegue antes de continuar con el siguiente paso del script.
    const factory = await CFPFactory.deploy();
    await factory.waitForDeployment();

    console.log(`CFPFactory desplegado en: ${await factory.getAddress()}`);
}

// Ejecutar la función main y manejar cualquier error que pueda ocurrir durante el proceso de despliegue.
main().catch((error) => {
    console.error(error);
    process.exitCode = 1;
});
