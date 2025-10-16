# Run tests

1. Create a Python virtual environment (recommended)

2. Install the dependencies with the following command:

  ```bash
  pip install ".[api,dev,test]"
  ```

3. To run the tests, you can use the following command:

  ```bash
    make test-unit
      
    # Open the HTML coverage report
    open htmlcov/index.html  # macOS
    # xdg-open htmlcov/index.html  # Linux
  ```
