
import { expect } from "chai";
import * as ethers from "ethers";
const { Wallet, decodeBytes32String, encodeBytes32String } = ethers;
import hre from "hardhat";

async function loadFixture(fixture) {
  const { networkHelpers } = await hre.network.connect();
  return networkHelpers.loadFixture(fixture);
}

async function signerAddress(signer) {
  return signer.getAddress();
}

async function signerAddresses(signers) {
  return Promise.all(signers.map((signer) => signerAddress(signer)));
}

function randInt(min, max) {
  return Math.floor(Math.random() * (max - min + 1)) + min;
}

describe("Ballot", function () {
  const toBytes32 = encodeBytes32String;
  const fromBytes32 = decodeBytes32String;
  const languages = ["Alemán", "Búlgaro", "Chino", "Danés", "Español"];

  async function deployBallotFixture() {
    const { ethers } = await hre.network.connect();
    const accounts = await ethers.getSigners();
    const Ballot = await ethers.getContractFactory("Ballot");
    const ballot = await Ballot.deploy(languages.map(toBytes32));
    return { ballot, accounts };
  }

  async function votingFixture() {
    const { ballot, accounts } = await loadFixture(deployBallotFixture);
    await ballot.giveAllRightToVote(await signerAddresses(accounts.slice(1)));
    await ballot.start();
    return { ballot, accounts };
  }

  async function endVotingFixture() {
    const { ballot, accounts } = await loadFixture(votingFixture);
    for (let i = 1; i < accounts.length; i++) {
      await ballot.connect(accounts[i]).vote(i % languages.length);
    }
    await ballot.end();
    return { ballot, accounts };
  }


  describe("Deployment", function () {
    it("Should reject less than two proposals", async function () {
      const { ethers } = await hre.network.connect();
      const Ballot = await ethers.getContractFactory("Ballot");
      await expect(Ballot.deploy([toBytes32("Proposal 1")])).to.be.revertedWith("There should be at least two proposals.");
    });

    it("Should have the right number of proposals", async function () {
      const { ballot } = await loadFixture(deployBallotFixture);
      expect(await ballot.numProposals()).to.equal(languages.length);
    });

    it("Should have the correct proposal names", async function () {
      const { ballot } = await loadFixture(deployBallotFixture);
      for (let i = 0; i < languages.length; i++) {
        const proposal = await ballot.proposals(i);
        expect(fromBytes32(proposal.name)).to.equal(languages[i]);
      }
    });
    it("Should set the chairperson to the deployer", async function () {
      const { ballot, accounts } = await loadFixture(deployBallotFixture);
      expect(await ballot.chairperson()).to.equal(await signerAddress(accounts[0]));
    });
    it("Should not have started voting", async function () {
      const { ballot } = await loadFixture(deployBallotFixture);
      expect(await ballot.started()).to.be.false;
    });
    it("Shold not have ended voting", async function () {
      const { ballot } = await loadFixture(deployBallotFixture);
      expect(await ballot.ended()).to.be.false;
    });
    it("Should have no voters initially", async function () {
      const { ballot } = await loadFixture(deployBallotFixture);
      expect(await ballot.numVoters()).to.equal(0);
    });
  });

  describe("Starting", function () {
    it("Should allow chairperson to give right to vote", async function () {
      const { ballot, accounts } = await loadFixture(deployBallotFixture);
      const account1Address = await signerAddress(accounts[1]);
      await ballot.giveRightToVote(account1Address);
      const voter = await ballot.voters(account1Address);
      expect(voter.canVote).to.be.true;
    });

    it("Should not allow others to give right to vote", async function () {
      const { ballot, accounts } = await loadFixture(deployBallotFixture);
      const account2Address = await signerAddress(accounts[2]);
      await expect(ballot.connect(accounts[randInt(1, accounts.length - 1)]).giveRightToVote(account2Address)).to.be.revertedWith("Only chairperson can invoke this function.");
    });

    it("Should allow chairperson to call giveAllRightToVote", async function () {
      const { ballot, accounts } = await loadFixture(deployBallotFixture);
      const addresses = await signerAddresses(accounts.slice(1));
      await ballot.giveAllRightToVote(addresses);
      for (let i = 1; i < accounts.length; i++) {
        const voter = await ballot.voters(await signerAddress(accounts[i]));
        expect(voter.canVote).to.be.true;
      }
      expect(await ballot.numVoters()).to.equal(accounts.length - 1);
    });

    it("Should allow chairperson to withdraw right to vote", async function () {
      const { ballot, accounts } = await loadFixture(deployBallotFixture);
      const account1Address = await signerAddress(accounts[1]);
      await ballot.giveRightToVote(account1Address);
      let voter = await ballot.voters(account1Address);
      expect(voter.canVote).to.be.true;
      await ballot.withdrawRightToVote(account1Address);
      voter = await ballot.voters(account1Address);
      expect(voter.canVote).to.be.false;
      expect(await ballot.numVoters()).to.equal(0);
    });

    it("Should not allow withdrawing right to vote if not given", async function () {
      const { ballot, accounts } = await loadFixture(deployBallotFixture);
      await expect(ballot.withdrawRightToVote(await signerAddress(accounts[1]))).to.be.revertedWith("Voter has no right to vote");
    });

    it("Should not allow others to withdraw right to vote", async function () {
      const { ballot, accounts } = await loadFixture(deployBallotFixture);
      const account1Address = await signerAddress(accounts[1]);
      await ballot.giveRightToVote(account1Address);
      for (let i = 1; i < accounts.length; i++) {
        await expect(ballot.connect(accounts[i]).withdrawRightToVote(account1Address)).to.be.revertedWith("Only chairperson can invoke this function.");
      }
    });

    it("Should not allow giving right to vote twice", async function () {
      const { ballot, accounts } = await loadFixture(deployBallotFixture);
      const account1Address = await signerAddress(accounts[1]);
      await ballot.giveRightToVote(account1Address);
      await expect(ballot.giveRightToVote(account1Address)).to.be.revertedWith("Voter already has right to vote");
    });

    it("Should not allow voting before starting", async function () {
      const { ballot, accounts } = await loadFixture(deployBallotFixture);
      await ballot.giveRightToVote(await signerAddress(accounts[1]));
      await expect(ballot.connect(accounts[1]).vote(0)).to.be.revertedWith("Voting has not started yet.");
    });

    it("Should allow chairperson to start voting", async function () {
      const { ballot, accounts } = await loadFixture(deployBallotFixture);
      await ballot.start();
      expect(await ballot.started()).to.be.true;
    });

    it("Should not allow starting voting twice", async function () {
      const { ballot } = await loadFixture(deployBallotFixture);
      await ballot.start();
      await expect(ballot.start()).to.be.revertedWith("Voting has already started.");
    });

    it("Should not allow others to start voting", async function () {
      const { ballot, accounts } = await loadFixture(deployBallotFixture);
      for (let i = 1; i < accounts.length; i++) {
        await expect(ballot.connect(accounts[i]).start()).to.be.revertedWith("Only chairperson can invoke this function.");
      }
    });

    it("Should not allow ending voting before starting", async function () {
      const { ballot } = await loadFixture(deployBallotFixture);
      await expect(ballot.end()).to.be.revertedWith("Voting has not started yet.");
    });
  });

  describe("Voting", function () {


    it("Should have zero votes initially", async function () {
      const { ballot } = await loadFixture(votingFixture);
      for (let i = 0; i < languages.length; i++) {
        const proposal = await ballot.proposals(i);
        expect(proposal.voteCount).to.equal(0);
      }
    });

    it("Should not allow giving right to vote after starting", async function () {
      const { ballot, accounts } = await loadFixture(votingFixture);
      const newVoter = Wallet.createRandom().address;
      await expect(ballot.giveRightToVote(newVoter)).to.be.revertedWith("Voting has already started.");
    });

    it("Should not allow calling giveAllRightToVote after starting", async function () {
      const { ballot } = await loadFixture(votingFixture);
      await expect(ballot.giveAllRightToVote([Wallet.createRandom().address])).to.be.revertedWith("Voting has already started.");
    });

    it("Should allow voters to vote", async function () {
      const { ballot, accounts } = await loadFixture(votingFixture);
      await ballot.connect(accounts[1]).vote(0);
      const voter = await ballot.voters(await signerAddress(accounts[1]));
      expect(voter.voted).to.be.true;
      expect(voter.vote).to.equal(0);
      const proposal = await ballot.proposals(0);
      expect(proposal.voteCount).to.equal(1);
    });

    it("Should not allow double voting", async function () {
      const { ballot, accounts } = await loadFixture(votingFixture);
      await ballot.connect(accounts[1]).vote(0);
      await expect(ballot.connect(accounts[1]).vote(0)).to.be.revertedWith("Already voted.");
    });

    it("Should not allow voting without right", async function () {
      const { ballot, accounts } = await loadFixture(deployBallotFixture);
      await ballot.start();
      for (let account of accounts) {
        await expect(ballot.connect(account).vote(0)).to.be.revertedWith("Has no right to vote");
      }
    });

    it("Should not allow voting for non-existent proposal", async function () {
      const { ballot, accounts } = await loadFixture(votingFixture);
      await expect(ballot.connect(accounts[1]).vote(languages.length)).to.revert(ethers);
    });

    it("Should register votes correctly", async function () {
      const { ballot, accounts } = await loadFixture(votingFixture);
      await ballot.connect(accounts[1]).vote(0);
      await ballot.connect(accounts[2]).vote(1);
      await ballot.connect(accounts[3]).vote(2);
      await ballot.connect(accounts[4]).vote(0);

      expect((await ballot.proposals(0)).voteCount).to.equal(2);
      expect((await ballot.proposals(1)).voteCount).to.equal(1);
      expect((await ballot.proposals(2)).voteCount).to.equal(1);
    });

    it("Should not show winningProposals before ending", async function () {
      const { ballot } = await loadFixture(votingFixture);
      await expect(ballot.winningProposals()).to.be.revertedWith("Voting has not ended yet.");
    });

    it("Should not show winners before ending", async function () {
      const { ballot } = await loadFixture(votingFixture);
      await expect(ballot.winners()).to.be.revertedWith("Voting has not ended yet.");
    });

  });

  describe("After voting ends", function () {

    it("Should allow chairperson to end voting", async function () {
      const { ballot } = await loadFixture(endVotingFixture);
      expect(await ballot.ended()).to.be.true;
    });

    it("Should not allow ending voting twice", async function () {
      const { ballot } = await loadFixture(endVotingFixture);
      await expect(ballot.end()).to.be.revertedWith("Voting has already ended.");
    });

    it("Should not allow starting voting after ending", async function () {
      const { ballot } = await loadFixture(endVotingFixture);
      await expect(ballot.start()).to.revert(ethers);
    });

    it("Should not allow voting after ending", async function () {
      const { ballot, accounts } = await loadFixture(votingFixture);
      await ballot.end();
      for (let i = 1; i < accounts.length; i++) {
        await expect(ballot.connect(accounts[i]).vote(0)).to.be.revertedWith("Voting has already ended.");
      }
    });

    it("Should not allow giving right to vote after ending", async function () {
      const { ballot } = await loadFixture(endVotingFixture);
      const newVoter = Wallet.createRandom().address;
      await expect(ballot.giveRightToVote(newVoter)).to.revert(ethers);
    });

    it("Should not allow others to end voting", async function () {
      const { ballot, accounts } = await loadFixture(votingFixture);
      for (let i = 1; i < accounts.length; i++) {
        await expect(ballot.connect(accounts[i]).end()).to.be.revertedWith("Only chairperson can invoke this function.");
      }
    });

    it("Should record the correct number of votes", async function () {
      const { ballot, accounts } = await loadFixture(endVotingFixture);
      const votesPerProposal = Array(languages.length).fill(0);
      for (let i = 1; i < accounts.length; i++) {
        const proposalIndex = i % languages.length;
        votesPerProposal[proposalIndex]++;
      }
      for (let i = 0; i < languages.length; i++) {
        const proposal = await ballot.proposals(i);
        expect(proposal.voteCount).to.equal(votesPerProposal[i]);
      }
    });

    it("Should return correct winning proposals", async function () {
      const { ballot } = await loadFixture(endVotingFixture);
      const expectedWinningProposals = [1, 2, 3, 4];
      const winningProposals = await ballot.winningProposals();
      expect(winningProposals.length).to.be.equal(expectedWinningProposals.length);
      for (let i = 0; i < winningProposals.length; i++) {
        expect(winningProposals[i]).to.be.equal(expectedWinningProposals[i]);
      }
    });

    it("Should return correct winner", async function () {
      const { ballot, accounts } = await loadFixture(votingFixture);
      for (let i = 1; i < accounts.length; i++) {
        await ballot.connect(accounts[i]).vote(i % 2);
      }
      await ballot.end();
      const winners = await ballot.winners();
      expect(winners.length).to.be.equal(1);
      expect(fromBytes32(winners[0])).to.be.equal(languages[(accounts.length - 1) % 2]);
    });

    it("Should return correct winners", async function () {
      const { ballot } = await loadFixture(endVotingFixture);
      const expectedWinners = languages.slice(1);
      const winners = await ballot.winners();
      expect(winners.length).to.be.equal(expectedWinners.length);
      for (let i = 0; i < winners.length; i++) {
        expect(fromBytes32(winners[i])).to.be.equal(expectedWinners[i]);
      }
    });

    it("Should return an empty list of winning proposals if no votes", async function () {
      const { ballot } = await loadFixture(deployBallotFixture);
      await ballot.start();
      await ballot.end();
      const winningProposals = await ballot.winningProposals();
      expect(winningProposals.length).to.equal(0);
    });

    it("Should return an empty list of winners if no votes", async function () {
      const { ballot } = await loadFixture(deployBallotFixture);
      await ballot.start();
      await ballot.end();
      const winners = await ballot.winners();
      expect(winners.length).to.equal(0);
    });

  });

});
