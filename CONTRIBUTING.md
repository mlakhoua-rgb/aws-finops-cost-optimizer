# Contributing to AWS FinOps Cost Optimizer

First off, thank you for considering contributing to this project! Your help is greatly appreciated. This is an educational project designed to help the community learn and implement FinOps best practices on AWS.

## How Can I Contribute?

### Reporting Bugs
If you find a bug, please open an issue and provide the following information:
- A clear and descriptive title.
- A detailed description of the problem, including steps to reproduce it.
- The expected behavior and what you observed instead.
- Your environment details (OS, Python version, Terraform version, etc.).

### Suggesting Enhancements
If you have an idea for a new feature or an improvement to an existing one, please open an issue to discuss it. This allows us to align on the proposal before you put in the effort to write code.

### Pull Requests
We welcome pull requests! Please follow these steps:
1. Fork the repository.
2. Create a new branch for your feature or bug fix (`git checkout -b feature/my-new-feature`).
3. Make your changes and commit them with a clear, descriptive message.
4. Ensure your code adheres to the existing style and includes tests where applicable.
5. Push your branch to your fork (`git push origin feature/my-new-feature`).
6. Open a pull request against the `main` branch of this repository.

## Styleguides

### Python Code
- Follow the [PEP 8](https://www.python.org/dev/peps/pep-0008/) style guide.
- Use `black` for code formatting.
- Add type hints to your functions.
- Write clear, concise comments where necessary.

### Terraform Code
- Use the standard Terraform formatting (`terraform fmt`).
- Follow the official [Terraform style conventions](https://www.terraform.io/docs/language/style.html).
- Use descriptive names for variables and resources.

### Commit Messages
- Use the [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) format.
- Example: `feat: add support for spot instance recommendations`

## Code of Conduct
This project and everyone participating in it is governed by our [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code. Please report unacceptable behavior to [mo@metafive.one](mailto:mo@metafive.one).
