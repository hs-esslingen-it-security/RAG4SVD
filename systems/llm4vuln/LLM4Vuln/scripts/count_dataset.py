from dataloader import SolidityLoader, JavaLoader


def run():
    solidity_lengths = []
    java_lengths = []

    solidity_loader = SolidityLoader()

    for code, _, _ in solidity_loader.load():
        length = len(code.get_all_str().splitlines())
        solidity_lengths.append(length)

    java_loader = JavaLoader()

    for code, _, _ in java_loader.load():
        length = len(code.get_all_str().splitlines())
        java_lengths.append(length)

    print(f"Solidity: Min={min(solidity_lengths)}, Max={max(solidity_lengths)}, Average={sum(solidity_lengths)/len(solidity_lengths)}")
    print(f"Java: Min={min(java_lengths)}, Max={max(java_lengths)}, Average={sum(java_lengths)/len(java_lengths)}")

