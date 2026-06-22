import sys

# ============================================
# Fix 1: RawAlert — add source_id
# ============================================
path = r"nozzle\domain\schemas.py"
with open(path, "r", encoding="utf-8") as f:
    c = f.read()

old1 = 'class RawAlert(BaseModel):\n    """Сырой алерт от источника до нормализации."""\n    external_id: str = Field(..., description="ID алерта во внешней системе")\n    source_type: SourceType\n    raw_payload: dict = Field(..., description="Полный JSON от источника")\n    received_at: datetime = Field(default_factory=datetime.utcnow)'
new1 = 'class RawAlert(BaseModel):\n    """Сырой алерт от источника до нормализации."""\n    external_id: str = Field(..., description="ID алерта во внешней системе")\n    source_type: SourceType\n    source_id: UUID = Field(..., description="ID источника в нашей системе")\n    raw_payload: dict = Field(..., description="Полный JSON от источника")\n    received_at: datetime = Field(default_factory=datetime.utcnow)'

if old1 in c:
    c = c.replace(old1, new1)
    print("Fix 1: source_id added to RawAlert")
else:
    print("Fix 1: pattern not found - may already be fixed")

# Fix 5: metadata -> extra_data
old5 = "metadata: dict = Field(default_factory=dict)"
new5 = "extra_data: dict = Field(default_factory=dict)"
if old5 in c:
    c = c.replace(old5, new5)
    print("Fix 5: metadata -> extra_data in NormalizedAlert")
else:
    print("Fix 5: pattern not found")

# Fix 2: severity SeverityLevel -> int
old2 = "severity: SeverityLevel = SeverityLevel.INFO"
new2 = "severity: int = 0"
if old2 in c:
    c = c.replace(old2, new2)
    print("Fix 2: severity changed to int")

with open(path, "w", encoding="utf-8") as f:
    f.write(c)

# ============================================
# Fix 1b: WazuhAdapter — pass source_id
# ============================================
path2 = r"nozzle\ingestion\wazuh.py"
with open(path2, "r", encoding="utf-8") as f:
    c2 = f.read()

old_w = 'yield RawAlert(\n                    external_id=item.get("id", ""),\n                    source_type=SourceType.WAZUH,\n                    raw_payload=item,\n                    received_at=datetime.utcnow(),\n                )'
new_w = 'yield RawAlert(\n                    external_id=item.get("id", ""),\n                    source_type=SourceType.WAZUH,\n                    source_id=UUID(self.source_id),\n                    raw_payload=item,\n                    received_at=datetime.utcnow(),\n                )'

if old_w in c2:
    c2 = c2.replace(old_w, new_w)
    print("Fix 1b: source_id in WazuhAdapter")
else:
    print("Fix 1b: pattern not found in wazuh.py")

# Fix 3: disconnect DELETE
old_d = 'await self._client.post(f"{self.base_url}/security/user/authenticate")'
new_d = 'await self._client.delete(f"{self.base_url}/security/user/authenticate")'
if old_d in c2:
    c2 = c2.replace(old_d, new_d)
    print("Fix 3: disconnect() uses DELETE")

# Add UUID import if missing
if "from uuid import UUID" not in c2:
    c2 = c2.replace("from datetime import datetime", "from datetime import datetime\nfrom uuid import UUID")
    print("Fix 1b: UUID import added")

with open(path2, "w", encoding="utf-8") as f:
    f.write(c2)

# ============================================
# Fix 2b: ClusteringManager severity
# ============================================
path3 = r"nozzle\clustering\manager.py"
with open(path3, "r", encoding="utf-8") as f:
    c3 = f.read()

old_c = "severity=a.severity if a.severity in (0,3,5,8,12,15) else 0,"
new_c = "severity=a.severity,"
if old_c in c3:
    c3 = c3.replace(old_c, new_c)
    print("Fix 2b: severity in ClusteringManager")
else:
    print("Fix 2b: pattern not found in manager.py")

with open(path3, "w", encoding="utf-8") as f:
    f.write(c3)

# ============================================
# Fix 4: clusters.py source_type
# ============================================
path4 = r"nozzle\api\v1\clusters.py"
with open(path4, "r", encoding="utf-8") as f:
    c4 = f.read()

old_cl = 'source_type="wazuh"'
new_cl = 'source_type=a.source.type.value if a.source else "unknown"'
if old_cl in c4:
    c4 = c4.replace(old_cl, new_cl)
    print("Fix 4: dynamic source_type in clusters.py")
else:
    print("Fix 4: pattern not found")

with open(path4, "w", encoding="utf-8") as f:
    f.write(c4)

# ============================================
# Fix 6: pyproject.toml author
# ============================================
path5 = r"pyproject.toml"
with open(path5, "r", encoding="utf-8") as f:
    c5 = f.read()

old_a = '{name = "Your Name", email = "you@example.com"}'
new_a = '{name = "misha622"}'
if old_a in c5:
    c5 = c5.replace(old_a, new_a)
    print("Fix 6: author updated")
else:
    print("Fix 6: author pattern not found")

with open(path5, "w", encoding="utf-8") as f:
    f.write(c5)

print("\nAll fixes applied.")
