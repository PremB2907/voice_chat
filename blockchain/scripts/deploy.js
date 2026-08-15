const hre = require("hardhat");
const fs = require("fs");
const path = require("path");

async function main() {
  console.log("Starting deployment...");

  const [deployer] = await hre.ethers.getSigners();
  console.log("Deploying contract with account:", deployer.address);

  const Registry = await hre.ethers.getContractFactory("MemoryBridgeRegistry");
  const registry = await Registry.deploy();

  await registry.waitForDeployment();
  const contractAddress = await registry.getAddress();

  console.log("MemoryBridgeRegistry deployed to:", contractAddress);

  // Read ABI
  const artifactPath = path.join(__dirname, "../artifacts/contracts/MemoryBridgeRegistry.sol/MemoryBridgeRegistry.json");
  const artifact = JSON.parse(fs.readFileSync(artifactPath, "utf8"));

  const config = {
    contract_address: contractAddress,
    abi: artifact.abi,
    deployer: deployer.address,
    chain_id: 1337
  };

  const rootConfigPath = path.join(__dirname, "../../blockchain_config.json");
  fs.writeFileSync(rootConfigPath, JSON.stringify(config, null, 2));
  console.log("Saved config to:", rootConfigPath);
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });
