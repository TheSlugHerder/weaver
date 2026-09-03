# Bandit Low-Severity Findings

Report generated: .bandit-report.json

Summary: 22 low-severity findings from `bandit -r src`.

List of findings:

1. File: `src/weaver/auth.py` (line 129)
   - Test: B105 (hardcoded_password_string)
   - Issue: Possible hardcoded password: 'bearer'
   - More: https://bandit.readthedocs.io/en/1.9.4/plugins/b105_hardcoded_password_string.html
   - Code excerpt: `token = jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")`

2. File: `src/weaver/db.py` (line 22)
   - Test: B110 (try_except_pass)
   - Issue: Try, Except, Pass detected.
   - More: https://bandit.readthedocs.io/en/1.9.4/plugins/b110_try_except_pass.html
   - Code excerpt: `except Exception:\n    pass`

3. File: `src/weaver/game/dnd_adapter.py` (line 34)
   - Test: B110 (try_except_pass)
   - Issue: Try, Except, Pass detected.
   - Code excerpt: `except Exception:\n    pass`

4. File: `src/weaver/game/dnd_adapter.py` (line 38)
   - Test: B311 (blacklist)
   - Issue: Use of `random` (not suitable for crypto/security purposes).
   - More: https://bandit.readthedocs.io/en/1.9.4/blacklists/blacklist_calls.html#b311-random
   - Code excerpt: `roll = random.randint(1, 20)`

5. File: `src/weaver/game/dnd_adapter.py` (line 44)
   - Test: B311 (blacklist)
   - Issue: Use of `random.randint` for damage calculation.
   - Code excerpt: `damage = random.randint(1, 8) + int(attacker.get("damage_mod", 0))`

6. File: `src/weaver/game/dnd_adapter.py` (line 60)
   - Test: B110 (try_except_pass)
   - Issue: Try, Except, Pass detected.

7. File: `src/weaver/game/dnd_adapter.py` (line 63)
   - Test: B311 (blacklist)
   - Issue: Use of `random.randint` for saves.

8. File: `src/weaver/game/dnd_adapter.py` (line 80)
   - Test: B110 (try_except_pass)
   - Issue: Try, Except, Pass detected.

9. File: `src/weaver/game/dnd_adapter.py` (line 87)
   - Test: B311 (blacklist)
   - Issue: Use of `random.randint`.

10. File: `src/weaver/game/turns.py` (line 49)
    - Test: B110 (try_except_pass)
    - Issue: Try, Except, Pass detected.

11. File: `src/weaver/game/worker.py` (line 71)
    - Test: B110 (try_except_pass)
    - Issue: Try, Except, Pass detected.

12. File: `src/weaver/main.py` (line 75)
    - Test: B110 (try_except_pass)
    - Issue: Try, Except, Pass detected when attempting to initialize redis/db.

13. File: `src/weaver/rate_limiter.py` (line 41)
    - Test: B110 (try_except_pass)
    - Issue: Try, Except, Pass detected when setting metrics on redis connect.

14. File: `src/weaver/rate_limiter.py` (line 48)
    - Test: B110 (try_except_pass)
    - Issue: Try, Except, Pass detected when reporting redis down.

15. File: `src/weaver/rate_limiter.py` (line 82)
    - Test: B110 (try_except_pass)
    - Issue: Try, Except, Pass detected around redis connect logging.

16. File: `src/weaver/rate_limiter.py` (line 91)
    - Test: B110 (try_except_pass)
    - Issue: Try, Except, Pass detected during retry/backoff handling.

17. File: `src/weaver/rate_limiter.py` (line 99)
    - Test: B110 (try_except_pass)
    - Issue: Try, Except, Pass detected while finalizing redis init.

18. File: `src/weaver/rate_limiter.py` (line 177)
    - Test: B110 (try_except_pass)
    - Issue: Try, Except, Pass detected when updating metrics after increment.

19. File: `src/weaver/rate_limiter.py` (line 184)
    - Test: B110 (try_except_pass)
    - Issue: Try, Except, Pass detected when incrementing fallback metrics.

20. File: `src/weaver/rate_limiter.py` (line 226)
    - Test: B110 (try_except_pass)
    - Issue: Try, Except, Pass detected while closing redis connection.

21. File: `src/weaver/rate_limiter.py` (line 229)
    - Test: B110 (try_except_pass)
    - Issue: Try, Except, Pass detected on best-effort close.

22. File: `src/weaver/rate_limiter.py` (line 232)
    - Test: B110 (try_except_pass)
    - Issue: Try, Except, Pass detected resetting `_redis = None` cleanup.

Notes:
- Most findings are `try/except: pass` patterns and use of the `random` module where cryptographic randomness is not required (game logic); these are low severity but worth addressing for maintainability and clarity.
- The `hardcoded 'bearer'` note in `auth.py` is a string literal used in token type responses and can be suppressed or documented.

Recommendation: review each `try/except: pass` block and either handle/log specific exceptions or add a brief comment explaining why the broad except is acceptable.
