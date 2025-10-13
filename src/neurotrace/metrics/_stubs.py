"""
Stub functions for missing MVP metrics.
These are placeholders with signatures and docstrings only - no runtime side effects.
"""

def compute_branching_factor(messages):
    """Compute branching factor per conversation.

    Parameters:
    - messages: iterable of message records with fields: id, parent_id, conversation_id

    Returns:
    - dict mapping conversation_id -> { 'avg_branching': float, 'max_branching': int }
    """
    pass


def compute_clarity_debt(breadcrumbs, clarification_threshold=1):
    """Compute clarity debt per conversation.

    Definition: number of clarification turns beyond a threshold after a user prompt.

    Parameters:
    - breadcrumbs: DataFrame-like with columns: role, message_id, parent_id, timestamp, top_zone
    - clarification_threshold: int threshold turns after a user prompt

    Returns:
    - DataFrame-like with columns: conversation_id, clarity_debt
    """
    pass


def compute_jumpiness(breadcrumbs, window=20):
    """Compute jumpiness: zone/topic switches per N assistant turns.

    Parameters:
    - breadcrumbs: DataFrame-like with columns: role, top_zone, conversation_id
    - window: number of assistant turns to normalize by

    Returns:
    - DataFrame-like with columns: conversation_id, jumpiness
    """
    pass


def compute_stability(breadcrumbs, by='week'):
    """Compute stability: KL-divergence of zone mix across time buckets.

    Parameters:
    - breadcrumbs: DataFrame-like with columns: timestamp, role, top_zone, conversation_id
    - by: str time bucket ('week' | 'month')

    Returns:
    - DataFrame-like with columns: conversation_id, bucket, stability_kl
    """
    pass
