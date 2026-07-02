name: Pull Request
description: Submit a pull request to MemPalace Evolve
title: "[PR] "
labels: []
assignees: []
body:
  - type: markdown
    attributes:
      value: |
        Thanks for taking the time to contribute! Please fill out the details below.
  - type: textarea
    id: description
    attributes:
      label: Description
      description: Describe the changes in this pull request
      placeholder: A clear and concise description of the changes
    validations:
      required: true
  - type: dropdown
    id: type
    attributes:
      label: Type of change
      multiple: true
      options:
        - Bug fix
        - New feature
        - Documentation update
        - Code refactor
        - Test update
        - Other
    validations:
      required: true
  - type: textarea
    id: testing
    attributes:
      label: How has this been tested?
      description: Describe the tests you ran
      placeholder: |
        - python -m pytest tests/ -v
        - Manual testing with ...
    validations:
      required: false
  - type: checkboxes
    id: checklist
    attributes:
      label: Checklist
      options:
        - label: I have added tests that prove my fix/feature works
        - label: I have updated documentation accordingly
        - label: My code follows the project's code style
        - label: All existing tests pass
