package returnguard.policy

# By default, we do NOT allow the return
default allow = false

# Allow if there are no violations
allow {
    count(violations) == 0
}

# Define the rules for violations
violations[msg] {
    input.days_since_order > 30
    msg := "item_outside_return_window"
}

violations[msg] {
    input.fraud_score > 80
    msg := "fraud_score_too_high"
}

violations[msg] {
    contains(lower(input.product_name), "clearance")
    msg := "clearance_items_final_sale"
}
