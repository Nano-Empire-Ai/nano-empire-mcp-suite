import unittest
from nano_mcp_suite.a2a_delegator import A2ADelegator

class TestA2ADelegation(unittest.TestCase):
    def setUp(self):
        self.delegator = A2ADelegator()

    def test_delegation_flow(self):
        # 1. Queue a task
        task_id = self.delegator.delegate_task(
            client_agent_id="test_partner_agent",
            task_type="audit_smart_contract",
            payload={"contract_address": "0x123456789abcdef", "language": "solidity"},
            receipt_tx="tx_mock_payment_12345"
        )
        self.assertTrue(task_id.startswith("a2a_"))

        # 2. Check task status
        task = self.delegator.get_task(task_id)
        self.assertIsNotNone(task)
        self.assertEqual(task["client_agent_id"], "test_partner_agent")
        self.assertEqual(task["status"], "queued")
        self.assertEqual(task["payload"]["language"], "solidity")

        # 3. Complete task
        self.delegator.complete_task(task_id, {"vulnerabilities_found": 0, "status": "secure"})
        updated_task = self.delegator.get_task(task_id)
        self.assertEqual(updated_task["status"], "completed")
        self.assertEqual(updated_task["result"]["vulnerabilities_found"], 0)

if __name__ == "__main__":
    unittest.main()
