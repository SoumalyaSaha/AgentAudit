# TICKET-142: Bulk discount not applied at exact 10-unit boundary

**Reported by:** QA
**Priority:** High

## Description

Customers ordering exactly 10 units are not receiving the advertised
10% bulk discount. Orders of 11+ units correctly receive the discount.
Orders of exactly 20 correctly receive the 20% discount.

## Expected behavior

`calculate_total(price, 10)` should apply the 10% discount tier
(quantity >= 10), matching the pricing page.

## Steps to reproduce

    calculate_total(10.0, 10)  # returns 100.0, expected 90.0

Please fix the boundary condition in the discount calculation logic.
