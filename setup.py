from setuptools import setup, find_packages

setup(
    name="iflow-mcp_bethington-cheat-engine-server-python",
    version="0.1.0",
    description="A Python MCP server for safe Cheat Engine functionality",
    packages=find_packages(),
    include_package_data=True,
    package_data={
        'server': ['**/*.json'],
    },
    entry_points={
        'console_scripts': [
            'iflow-mcp_bethington-cheat-engine-server-python = server.main:main',
        ],
    },
    install_requires=[
        "mcp>=1.0.0",
        "trio>=0.22.0", 
        "psutil>=5.9.0",
        "capstone>=5.0.0",
        "pyautogui>=0.9.54",
        "pillow>=10.0.0",
        "opencv-python>=4.8.0",
        "pywinauto>=0.6.8"
    ],
)