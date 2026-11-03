# Northstar replenishment policy

Demo policy, effective 2026-10-01. Review each warehouse/product combination
whose on_hand_units is strictly below reorder_point_units. A level equal to
the reorder point does not trigger review. Prioritize review using recent
unit sales and operational judgment; no automatic purchase order is created.
Always report the inventory snapshot date separately from the sales period.
Current stock and sales figures must come from governed tables, not memory.
