import asyncio
import unittest

from configstream.core import Proxy
from configstream.repositories import InMemoryProxyRepository


class TestInMemoryProxyRepository(unittest.TestCase):

    def setUp(self):
        self.repository = InMemoryProxyRepository()

    def test_save_and_get_all(self):
        asyncio.run(self.save_and_get_all_async())

    async def save_and_get_all_async(self):
        proxy1 = Proxy(config="test://proxy1", protocol="test", address="proxy1", port=8080)
        proxy2 = Proxy(config="test://proxy2", protocol="test", address="proxy2", port=8080)

        await self.repository.save(proxy1)
        await self.repository.save(proxy2)

        proxies = await self.repository.get_all()

        self.assertEqual(len(proxies), 2)
        self.assertIn(proxy1, proxies)
        self.assertIn(proxy2, proxies)

    def test_get_all_empty(self):
        asyncio.run(self.get_all_empty_async())

    async def get_all_empty_async(self):
        proxies = await self.repository.get_all()
        self.assertEqual(len(proxies), 0)


if __name__ == "__main__":
    unittest.main()
