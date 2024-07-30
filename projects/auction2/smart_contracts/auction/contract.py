from algopy import Account, ARC4Contract, Asset, Global, LocalState, Txn, UInt64, gtxn, itxn, op
from algopy.arc4 import abimethod


class Auction(ARC4Contract):
    # Auction
    # Start Price
    # Bid - Bid Price >  Start Price
    # Bid - Bid Price > Previous Bid
    # Bidder != Previous Bidder
    # Start Time - End Time
    # If Auction End -> End Time -> 0
    # Amount -> Claim
    def __init__(self) -> None:
        self.start_time = UInt64(0)  # Auction Start Time
        self.end_time = UInt64(0)  # Auction End Time
        self.asa_amount = UInt64(0)  # 1000 - bid price > asa amount
        self.asa = Asset()  # Token
        self.previous_bidder = Account()  # Previous Bidder
        self.claimble = LocalState(UInt64, key="claim", description="The claimle amount")  # Claimble Amount

    # Opt Asset #VBI token
    @abimethod
    def opt_into_asset(self, asset: Asset) -> None:  # đưa sản phầm vào đấu giá
        assert Txn.sender == Global.creator_address, "Only the creator can access"
        assert self.asa == 0, "ASA already exits"

        self.asa = asset
        itxn.AssetTransfer(asset_receiver=Global.current_application_address, xfer_asset=asset).submit()

    # Start Auction
    @abimethod
    def start_auction(
        self, start_price: UInt64, length: UInt64, axfer: gtxn.AssetTransferTransaction
    ) -> None:  # bắt đầu đấu giá
        assert Txn.sender == Global.creator_address, "Auction must be started by the creator"
        assert self.end_time == 0, "Auction ended"
        assert axfer.asset_receiver == Global.current_application_address, "Axfer must be to the current application"

        self.asa_amount = start_price
        self.end_time = Global.latest_timestamp + length
        self.previous_bidder = Txn.sender

    # Bids
    @abimethod
    def bid(self, pay: gtxn.PaymentTransaction) -> None:  # đấu giá
        # Check auction is ended or not
        assert Global.latest_timestamp <= self.end_time, "Auction ended"

        # verify payment
        assert Txn.sender == self.previous_bidder, "Bidder must be different"
        assert Txn.sender == pay.sender, "Bidder must be the sender"
        assert pay.amount > self.asa_amount, "Bid must be greater than the start price"

        # set data on global state
        self.asa_amount = pay.amount
        self.previous_bidder = Txn.sender

        # update claimble amount
        self.claimble[Txn.sender] = pay.amount

    # Claim Bids
    @abimethod
    def claim_asset(self, asset: Asset) -> None:  # chuyển sản phẩm đấu giá cho người thắng
        assert Txn.sender() == Global.creator_address, "Only the creator can access"
        assert Global.latest_timestamp > self.end_time, "Auction not ended"

        itxn.AssetTransfer(
            xfer_asset=asset,
            asset_receiver=self.previous_bidder,
            asset_close_to=self.previous_bidder,
            asset_amount=self.asa_amount,
        ).submit()

    @abimethod
    def clam_bids(self) -> None:
        amount = original_amount = self.claimble[Txn.sender]  # Lấy được token

        if Txn.sender == self.previous_bidder:
            amount -= self.asa_amount
        itxn.Payment(amount=amount, receiver=Txn.sender).submit()

        self.claimble[Txn.sender] = original_amount - amount

    # Delete Application
    @abimethod(allow_actions=["DeleteApplication"])
    def delete_application(self) -> None:
        itxn.Payment(
            close_remainder_to=Global.creator_address,
            receiver=Global.creator_address,
        ).submit()
