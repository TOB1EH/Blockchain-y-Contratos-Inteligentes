from eth_account import Account

Account.enable_unaudited_hdwallet_features()
admin = Account.from_mnemonic(
    "test test test test test test test test test test test junk",
    account_path="m/44'/60'/0'/0/2"
)
print(admin.address)