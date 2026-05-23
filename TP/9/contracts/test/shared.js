import * as ethers from "ethers";

export function now() {
  return Math.trunc(new Date().getTime() / 1000);
}

export class HashGenerator {
  constructor() {
    this.seed = 0;
  }

  next() {
    this.seed++;
    return this.current();
  }

  current() {
    return this.get(this.seed);
  }

  get(seed) {
    return ethers.keccak256(ethers.toBeHex(seed, 32));
  }

  set(seed) {
    this.seed = seed;
  }
}

export const emptyAddress = "0x0000000000000000000000000000000000000000";
