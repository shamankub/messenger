from setuptools import find_packages, setup

setup(
    name="messenger_server_Eseneev",
    version="0.0.1",
    description="messenger_server_Eseneev",
    author="Anton Eseneev",
    author_email="shaman_kub@mail.ru",
    packages=find_packages(),
    install_requires=["PyQt5", "sqlalchemy", "pycryptodome", "pycryptodomex"],
)
