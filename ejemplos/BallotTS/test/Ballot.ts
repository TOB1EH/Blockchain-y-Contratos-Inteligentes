import { expect } from "chai";
import hre from "hardhat";
import { encodeBytes32String, decodeBytes32String } from "ethers";

describe("Test Ballot", function () {

    async function deployBallotFixture() {
        const { ethers } = await hre.network.connect();
        const [owner, ...otherAccounts] = await ethers.getSigners();
        const ballot = await ethers.deployContract("Ballot", [[encodeBytes32String("Alice"), encodeBytes32String("Bob")]]);

        return { ballot, owner, otherAccounts };
    }

    it("should initialize proposals and chairperson correctly", async function () {
        const { networkHelpers } = await hre.network.connect();
        const { ballot, owner } = await networkHelpers.loadFixture(deployBallotFixture);
        expect(await ballot.numProposals()).to.equal(2);
        expect(await ballot.chairperson()).to.equal(owner.address);
        const proposal0 = await ballot.proposals(0);
        expect(decodeBytes32String(proposal0.name)).to.equal("Alice");
    });

    it("should only allow chairperson to give right to vote", async function () {
        const { networkHelpers } = await hre.network.connect();
        const { ballot, otherAccounts } = await networkHelpers.loadFixture(deployBallotFixture);
        await expect(ballot.connect(otherAccounts[0]).giveRightToVote(otherAccounts[1].address)).to.be.revertedWith(
            "Only chairperson can give right to vote."
        );
        await ballot.giveRightToVote(otherAccounts[0].address);
        const voter = await ballot.voters(otherAccounts[0].address);
        expect(voter.canVote).to.be.true;
        expect(await ballot.numVoters()).to.equal(1);
    });

    it("should not allow giving right to vote twice", async function () {
        const { networkHelpers } = await hre.network.connect();
        const { ballot, otherAccounts } = await networkHelpers.loadFixture(deployBallotFixture);
        await ballot.giveRightToVote(otherAccounts[0].address);
        await expect(ballot.giveRightToVote(otherAccounts[0].address)).to.be.revertedWith(
            "The voter already has the right to vote."
        );
    });

    it("should not allow voting without right", async function () {
        const { networkHelpers } = await hre.network.connect();
        const { ballot, owner, otherAccounts } = await networkHelpers.loadFixture(deployBallotFixture);
        for (const account of [owner, ...otherAccounts]) {
            await expect(ballot.connect(account).vote(0)).to.be.revertedWith("Has no right to vote");
        }
    });

    it("should allow voting and update vote count", async function () {
        const { networkHelpers } = await hre.network.connect();
        const { ballot, otherAccounts } = await networkHelpers.loadFixture(deployBallotFixture);
        await ballot.giveRightToVote(otherAccounts[0].address);
        await ballot.connect(otherAccounts[0]).vote(1);
        const proposal = await ballot.proposals(1);
        expect(proposal.voteCount).to.equal(1);
        const voter = await ballot.voters(otherAccounts[0].address);
        expect(voter.voted).to.be.true;
        expect(voter.vote).to.equal(1);
    });

    it("should not allow double voting", async function () {
        const { networkHelpers } = await hre.network.connect();
        const { ballot, otherAccounts } = await networkHelpers.loadFixture(deployBallotFixture);
        await ballot.giveRightToVote(otherAccounts[0].address);
        await ballot.connect(otherAccounts[0]).vote(0);
        await expect(ballot.connect(otherAccounts[0]).vote(1)).to.be.revertedWith("Already voted.");
    });

    it("should return correct winner after votes", async function () {
        const { networkHelpers } = await hre.network.connect();
        const { ballot, otherAccounts } = await networkHelpers.loadFixture(deployBallotFixture);
        await ballot.giveRightToVote(otherAccounts[0].address);
        await ballot.giveRightToVote(otherAccounts[1].address);
        await ballot.connect(otherAccounts[0]).vote(0);
        await ballot.connect(otherAccounts[1]).vote(1);
        // Tie, winner is first with max votes (index 0)
        expect(await ballot.winningProposal()).to.equal(0);
        expect(decodeBytes32String(await ballot.winnerName())).to.equal("Alice");

        // otherAccounts[2] votes for Bob, Bob wins
        await ballot.giveRightToVote(otherAccounts[2].address);
        await ballot.connect(otherAccounts[2]).vote(1);
        expect(await ballot.winningProposal()).to.equal(1);
        expect(decodeBytes32String(await ballot.winnerName())).to.equal("Bob");
    });

    it("should revert if proposal index is out of bounds", async function () {
        const { ethers, networkHelpers } = await hre.network.connect();
        const { ballot, otherAccounts } = await networkHelpers.loadFixture(deployBallotFixture);
        await ballot.giveRightToVote(otherAccounts[0].address);
        await expect(ballot.connect(otherAccounts[0]).vote(5)).to.revert(ethers);
    });

    it("should require at least 2 proposals", async function () {
        const { ethers } = await hre.network.connect();
        await expect(ethers.deployContract("Ballot", [[encodeBytes32String("OnlyOne")]])).to.be.revertedWith(
            "There should be at least 2 proposals"
        );
    });
});

// This test suite covers the functionality of the Ballot contract, including proposal initialization, voting rights management, voting process, and winner determination. It ensures that the contract behaves as expected under various scenarios, including edge cases like double voting and invalid proposal indices. The tests also verify that only the chairperson can grant voting rights and that the contract enforces the rules defined in its logic.