import { expect } from "chai";
import * as ethers from "ethers";
import hre from "hardhat";

async function loadFixture(fixture) {
  const { networkHelpers } = await hre.network.connect();
  return networkHelpers.loadFixture(fixture);
}

const toBytes32 = ethers.encodeBytes32String;
const fromBytes32 = ethers.decodeBytes32String;

describe("Test Ballot", function () {

    async function deployBallotFixture() {
        const { ethers } = await hre.network.connect();
        const accounts = await ethers.getSigners();
        const Ballot = await ethers.getContractFactory("Ballot");
        const ballot = await Ballot.deploy([toBytes32("Alice"), toBytes32("Bob")]);
        return { ballot, accounts };
    }

    it("should initialize proposals and chairperson correctly", async function () {
        const { ballot, accounts } = await loadFixture(deployBallotFixture);
        expect(await ballot.numProposals()).to.equal(2);
        expect(await ballot.chairperson()).to.equal(await accounts[0].getAddress());
        const proposal0 = await ballot.proposals(0);
        expect(fromBytes32(proposal0.name)).to.equal("Alice");
    });

    it("should only allow chairperson to give right to vote", async function () {
        const { ballot, accounts } = await loadFixture(deployBallotFixture);
        await expect(ballot.connect(accounts[1]).giveRightToVote(await accounts[2].getAddress())).to.be.revertedWith(
            "Only chairperson can give right to vote."
        );
        await ballot.giveRightToVote(await accounts[1].getAddress());
        const voter = await ballot.voters(await accounts[1].getAddress());
        expect(voter.canVote).to.be.true;
        expect(await ballot.numVoters()).to.equal(1);
    });

    it("should not allow giving right to vote twice", async function () {
        const { ballot, accounts } = await loadFixture(deployBallotFixture);
        await ballot.giveRightToVote(await accounts[1].getAddress());
        await expect(ballot.giveRightToVote(await accounts[1].getAddress())).to.be.revertedWith(
            "The voter already has the right to vote."
        );
    });

    it("should not allow voting without right", async function () {
        const { ballot, accounts } = await loadFixture(deployBallotFixture);
        for (let account of accounts) {
            await expect(ballot.connect(account).vote(0)).to.be.revertedWith("Has no right to vote");
        }
    });

    it("should allow voting and update vote count", async function () {
        const { ballot, accounts } = await loadFixture(deployBallotFixture);
        await ballot.giveRightToVote(await accounts[1].getAddress());
        await ballot.connect(accounts[1]).vote(1);
        const proposal = await ballot.proposals(1);
        expect(proposal.voteCount).to.equal(1);
        const voter = await ballot.voters(await accounts[1].getAddress());
        expect(voter.voted).to.be.true;
        expect(voter.vote).to.equal(1);
    });

    it("should not allow double voting", async function () {
        const { ballot, accounts } = await loadFixture(deployBallotFixture);
        await ballot.giveRightToVote(await accounts[1].getAddress());
        await ballot.connect(accounts[1]).vote(0);
        await expect(ballot.connect(accounts[1]).vote(1)).to.be.revertedWith("Already voted.");
    });

    it("should return correct winner after votes", async function () {
        const { ballot, accounts } = await loadFixture(deployBallotFixture);
        await ballot.giveRightToVote(await accounts[1].getAddress());
        await ballot.giveRightToVote(await accounts[2].getAddress());
        await ballot.connect(accounts[1]).vote(0);
        await ballot.connect(accounts[2]).vote(1);
        // Tie, winner is first with max votes (index 0)
        expect(await ballot.winningProposal()).to.equal(0);
        expect(fromBytes32(await ballot.winnerName())).to.equal("Alice");

        // addr3 votes for Bob, Bob wins
        await ballot.giveRightToVote(await accounts[3].getAddress());
        await ballot.connect(accounts[3]).vote(1);
        expect(await ballot.winningProposal()).to.equal(1);
        expect(fromBytes32(await ballot.winnerName())).to.equal("Bob");
    });

    it("should revert if proposal index is out of bounds", async function () {
        const { ballot, accounts } = await loadFixture(deployBallotFixture);
        await ballot.giveRightToVote(await accounts[1].getAddress());
        await expect(ballot.connect(accounts[1]).vote(5)).to.revert(ethers);
    });

    it("should require at least 2 proposals", async function () {
        const { ethers } = await hre.network.connect();
        const Ballot2 = await ethers.getContractFactory("Ballot");
        await expect(Ballot2.deploy([toBytes32("OnlyOne")])).to.be.revertedWith(
            "There should be at least 2 proposals"
        );
    });
});
