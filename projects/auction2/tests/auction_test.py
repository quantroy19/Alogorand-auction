import time
from collections.abc import Generator

import pytest
from algopy_testing import AlgopyTestContext, algopy_testing_context

from smart_contracts.auction.contract import Auction


@pytest.fixture()
def context() -> Generator[AlgopyTestContext, None, None]:
    with algopy_testing_context() as ctx:
        yield ctx
        ctx.reset()


def test_opt_into_asset(context: AlgopyTestContext):
    asset = context.any_asset()
    contract = Auction()

    # Call opt_into_asset from the context
    contract.opt_into_asset(asset)

    assert contract.asa.id == asset.id

    last_itxn = context.last_submitted_itxn.asset_transfer

    assert last_itxn.xfer_asset == asset
    assert last_itxn.asset_receiver == context.default_application.address


def test_start_auction(context: AlgopyTestContext):
    current_time = context.any_uint64(3, 9990)
    duration = context.any_uint64(1, 100)
    start_price = context.any_uint64(1, 400)

    contract = Auction()
    itxn_transfer = context.any_asset_transfer_transaction(
        asset_receiver=context.default_application.address, asset_amount=start_price
    )
    context.patch_global_fields(latest_timestamp=current_time)

    context.patch_txn_fields(sender=context.default_creator)
    contract.asa_amount = start_price
    contract.start_auction(start_price=start_price, length=duration, axfer=itxn_transfer)

    assert contract.asa_amount == start_price
    assert contract.end_time == current_time + duration
    assert contract.previous_bidder == context.default_creator


def test_bid(context: AlgopyTestContext):
    end_auction = context.any_uint64(min_value=int(time.time() + 10000))
    start_price = context.any_uint64(1, 100)
    account = context.default_creator
    pay_amount = context.any_uint64(int(start_price + 1), 1000)

    contract = Auction()

    contract.end_time = end_auction
    contract.previous_bidder = account
    contract.asa_amount = start_price
    pay = context.any_payment_transaction(sender=account, amount=pay_amount)
    contract.bid(pay)

    assert contract.asa_amount == pay_amount
    assert contract.previous_bidder == account
    assert contract.claimble[account] == pay_amount


def test_clam_bids(context: AlgopyTestContext):
    account = context.any_account()
    context.patch_txn_fields(sender=account)
    contract = Auction()
    claimable_amount = context.any_uint64()

    contract.claimble[account] = claimable_amount
    contract.previous_bidder = account
    previous_bid = context.any_uint64(max_value=int(claimable_amount))
    contract.asa_amount = previous_bid

    contract.clam_bids()

    amount = claimable_amount - previous_bid
    last_itxn = context.last_submitted_itxn.payment

    assert last_itxn.amount == amount
    assert last_itxn.receiver == account
    assert contract.claimble[account] == claimable_amount - amount
