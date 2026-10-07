package returnguard.policy

import rego.v1

# By default, we do NOT allow the return
default allow := false

# But we allow it if there are no violations
allow if {
    count(violations) == 0
}

# Define the rules for violations
violations contains "item_outside_return_window" if {
    input.days_since_order > 30
}

violations contains "fraud_score_too_high" if {
    input.fraud_score > 80
}

violations contains "clearance_items_final_sale" if {
    contains(lower(input.product_name), "clearance")
}
