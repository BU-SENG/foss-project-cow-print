# How to Contribute to AetherDB

First off, thank you for considering contributing! You're joining the **COW PRINT** team in building an awesome tool, and your help is invaluable.

We welcome all kinds of contributions:

* Adding new features
* Fixing bugs
* Improving documentation
* Submitting bug reports and feature requests

## 📜 Code of Conduct

This project and everyone participating in it is governed by our **[Code of Conduct](CODE_OF_CONDUCT.md)**. By participating, you are expected to uphold this code.

## 💻 Setting Up Your Development Environment

1. **Fork the Repository**
    Click the "Fork" button on the top-right of the `BU-SENG/foss-project-cow-print` repository page. This creates a copy of the project under your own GitHub account.

2. **Clone Your Fork**
    Clone your fork to your local machine (replace `[YourGitHubUsername]`):
    ```bash
    git clone [https://github.com/](https://github.com/)[YourGitHubUsername]/foss-project-cow-print.git
    cd foss-project-cow-print
    ```

3. **Create a Virtual Environment**
    It's highly recommended to work in a Python virtual environment:
    ```bash
    # On macOS/Linux
    python3 -m venv venv
    source venv/bin/activate

    # On Windows
    python -m venv venv
    .\venv\Scripts\activate
    ```

4. **Install Dependencies**
    Install the required libraries. (If a `requirements.txt` file exists, use `pip install -r requirements.txt`).
    ```bash
    pip install google-generativeai python-dotenv
    ```

5. **Set Up Environment Variables**
    Create a `.env` file in the root of the project. This file is ignored by Git and will not be pushed to GitHub. Add your API key:
    ```ini
    GEMINI_API_KEY="your_api_key_here"
    GEMINI_MODEL="models/gemini-2.5-pro"
    DEFAULT_DIALECT="mysql"
    ```

6. **Set Up the Upstream Remote**
    This allows you to pull changes from the main project repository to keep your fork up-to-date.
    ```bash
    git remote add upstream [https://github.com/BU-SENG/foss-project-cow-print.git](https://github.com/BU-SENG/foss-project-cow-print.git)
    ```

## 🧪 Running for Development

To test your changes, you can run the core engine just as a user would.

1. **Create a Test Schema:** Make a `schema.txt` file (or use an existing one) to test against.
2. **Run the Script:**
    ```bash
    python sqlm.py --schema schema.txt
    ```
3. Enter your natural language queries to see if your changes worked.

## 💡 Submitting a Pull Request (PR)

1. **Pull from Upstream**
    Make sure your local `main` branch is up-to-date with the main project.
    ```bash
    git checkout main
    git pull upstream main
    ```

2. **Create a New Branch**
    Create a descriptive branch name for your new feature or bugfix.
    ```bash
    git checkout -b feature/my-new-feature
    # or
    git checkout -b fix/fix-sql-generation-bug
    ```

3. **Make Your Changes**
    Write your code! Make sure to follow the project's coding style (e.g., PEP 8 for Python).

4. **Commit Your Changes**
    Write a clear and concise commit message.
   ```bash
    git add .
    git commit -m "feat: Add new dialect adapter for SQLite"
    ```

5. **Push to Your Fork**
    Push your new branch to your fork on GitHub.
    ```bash
    git push origin feature/my-new-feature
    ```

6. **Open a Pull Request**
    Go to the GitHub page for your fork, and you should see a prompt to "Compare & pull request". Click it, fill out the template, and submit your PR! The project maintainers will review it as soon as possible.

Thank you for your contribution!
