# CVE信息查询API文档

## 1. 接口概述

本文档描述了CVE信息查询API，该API允许外部系统查询CVE（通用漏洞披露）的详细信息，同时从cves、nvd和cisa三张数据表中获取相关数据。

## 2. 接口列表

### 2.1 单个CVE信息查询

**接口地址**：`/api/cve/{cve_id}`

**请求方法**：GET

**功能描述**：根据CVE ID查询单个CVE的详细信息，包括cves、nvd和cisa表中的数据。

**URL参数**：
- `cve_id`：CVE编号，格式为`CVE-YYYY-NNNN`，例如`CVE-2021-44228`

**请求示例**：
```
GET http://localhost:8010/api/cve/CVE-2021-44228
```

**响应格式**：
```json
{
  "error": false,
  "message": "查询成功",
  "data": {
    "cve_id": "CVE-2021-44228",
    "cves_table": {
      "cve_id": "CVE-2021-44228",
      "published_date": "2021-11-29 14:15:00",
      "last_modified_date": "2024-10-15 08:30:00",
      "description": "Apache Log4j2 远程代码执行漏洞",
      "base_score": 10.0,
      "base_severity": "CRITICAL",
      "attack_vector": "NETWORK",
      "attack_complexity": "LOW",
      "privileges_required": "NONE",
      "user_interaction": "NONE",
      "scope": "CHANGED",
      "confidentiality_impact": "HIGH",
      "integrity_impact": "HIGH",
      "availability_impact": "HIGH",
      "cwe_id": "CWE-77",
      "references": "https://nvd.nist.gov/vuln/detail/CVE-2021-44228"
    },
    "nvd_table": {
      "cve_id": "CVE-2021-44228",
      "published_date": "2021-11-29",
      "last_modified_date": "2024-10-15",
      "description": "Apache Log4j2 远程代码执行漏洞",
      "base_score": 10.0,
      "base_severity": "CRITICAL",
      "vector_string": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:H",
      "vendor": "Apache",
      "product": "Log4j"
    },
    "cisa_table": [
      {
        "vuln_id": "VU#840220",
        "vendor_project": "Apache",
        "product": "Log4j",
        "vulnerability_name": "Apache Log4j Remote Code Execution",
        "date_added": "2021-12-10",
        "short_description": "远程代码执行漏洞",
        "required_action": "更新至安全版本",
        "due_date": "2021-12-24",
        "cve_id": "CVE-2021-44228"
      }
    ],
    "timestamp": "2025-10-23 10:15:30"
  }
}
```

**错误响应示例**：
```json
{
  "error": true,
  "message": "无效的CVE ID格式，请使用标准格式如CVE-2021-44228"
}
```

```json
{
  "error": false,
  "message": "未找到CVE ID: CVE-2021-99999的相关信息",
  "data": null
}
```

### 2.2 批量CVE信息查询

**接口地址**：`/api/cve/batch`

**请求方法**：POST

**功能描述**：批量查询多个CVE ID的详细信息，每个CVE都会返回cves、nvd和cisa表中的相关数据。

**请求体格式**：
```json
{
  "cve_ids": ["CVE-2021-44228", "CVE-2021-22204", "CVE-2020-1472"]
}
```

**限制**：
- 单次最多查询50个CVE ID
- 每个CVE ID必须符合`CVE-YYYY-NNNN`格式

**请求示例**：
```
POST http://localhost:8010/api/cve/batch
Content-Type: application/json

{
  "cve_ids": ["CVE-2021-44228", "CVE-2021-22204"]
}
```

**响应格式**：
```json
{
  "error": false,
  "message": "批量查询成功",
  "data": {
    "results": [
      {
        "cve_id": "CVE-2021-44228",
        "cves_table": { /* 与单个查询返回结构相同 */ },
        "nvd_table": { /* 与单个查询返回结构相同 */ },
        "cisa_table": [ /* 与单个查询返回结构相同 */ ],
        "has_data": true
      },
      {
        "cve_id": "CVE-2021-22204",
        "cves_table": { /* 与单个查询返回结构相同 */ },
        "nvd_table": { /* 与单个查询返回结构相同 */ },
        "cisa_table": null,
        "has_data": true
      }
    ],
    "total": 2,
    "timestamp": "2025-10-23 10:15:30"
  }
}
```

**错误响应示例**：
```json
{
  "error": true,
  "message": "批量查询数量不能超过50个"
}
```

```json
{
  "error": true,
  "message": "无效的CVE ID格式: CVE-2021-123456789"
}
```

## 3. 数据说明

### 3.1 时间格式

所有时间字段均已转换为中国时区（UTC+8），格式为`YYYY-MM-DD HH:MM:SS`。

### 3.2 字段说明

**cves_table**（CVE基本信息表）：
- `cve_id`：CVE编号
- `published_date`：发布日期
- `last_modified_date`：最后修改日期
- `description`：漏洞描述
- `base_score`：基础分数（CVSS评分）
- `base_severity`：严重级别（CRITICAL/HIGH/MEDIUM/LOW）
- `attack_vector`：攻击向量
- `attack_complexity`：攻击复杂度
- `privileges_required`：所需权限
- `user_interaction`：用户交互需求
- `scope`：影响范围
- `confidentiality_impact`：保密性影响
- `integrity_impact`：完整性影响
- `availability_impact`：可用性影响
- `cwe_id`：CWE ID
- `references`：参考链接

**nvd_table**（国家漏洞数据库表）：
- `cve_id`：CVE编号
- `published_date`：发布日期
- `last_modified_date`：最后修改日期
- `description`：漏洞描述
- `base_score`：基础分数
- `base_severity`：严重级别
- `vector_string`：CVSS向量字符串
- `vendor`：厂商
- `product`：产品

**cisa_table**（美国网络安全与基础设施安全局表）：
- `vuln_id`：漏洞ID
- `vendor_project`：厂商/项目
- `product`：产品
- `vulnerability_name`：漏洞名称
- `date_added`：添加日期
- `short_description`：简短描述
- `required_action`：所需行动
- `due_date`：修复截止日期
- `cve_id`：关联的CVE编号

## 4. 调用示例

### 4.1 Python调用示例

**单个CVE查询**：
```python
import requests

cve_id = "CVE-2021-44228"
url = f"http://localhost:8010/api/cve/{cve_id}"

response = requests.get(url)
if response.status_code == 200:
    data = response.json()
    if not data['error']:
        print(f"CVE ID: {data['data']['cve_id']}")
        print(f"基础分数: {data['data']['cves_table'].get('base_score', 'N/A')}")
        print(f"严重级别: {data['data']['cves_table'].get('base_severity', 'N/A')}")
        print(f"描述: {data['data']['cves_table'].get('description', 'N/A')}")
    else:
        print(f"错误: {data['message']}")
else:
    print(f"请求失败: {response.status_code}")
```

**批量CVE查询**：
```python
import requests

url = "http://localhost:8010/api/cve/batch"
payload = {
    "cve_ids": ["CVE-2021-44228", "CVE-2021-22204", "CVE-2020-1472"]
}

response = requests.post(url, json=payload)
if response.status_code == 200:
    data = response.json()
    if not data['error']:
        for result in data['data']['results']:
            print(f"\nCVE ID: {result['cve_id']}")
            print(f"是否有数据: {result['has_data']}")
            if result['cves_table']:
                print(f"基础分数: {result['cves_table'].get('base_score', 'N/A')}")
                print(f"严重级别: {result['cves_table'].get('base_severity', 'N/A')}")
    else:
        print(f"错误: {data['message']}")
else:
    print(f"请求失败: {response.status_code}")
```

### 4.2 JavaScript调用示例

**单个CVE查询**：
```javascript
const cveId = 'CVE-2021-44228';
const url = `http://localhost:8010/api/cve/${cveId}`;

fetch(url)
  .then(response => response.json())
  .then(data => {
    if (!data.error) {
      console.log(`CVE ID: ${data.data.cve_id}`);
      console.log(`基础分数: ${data.data.cves_table?.base_score || 'N/A'}`);
      console.log(`严重级别: ${data.data.cves_table?.base_severity || 'N/A'}`);
      console.log(`描述: ${data.data.cves_table?.description || 'N/A'}`);
    } else {
      console.error(`错误: ${data.message}`);
    }
  })
  .catch(error => console.error('请求失败:', error));
```

**批量CVE查询**：
```javascript
const url = 'http://localhost:8010/api/cve/batch';
const data = {
  cve_ids: ['CVE-2021-44228', 'CVE-2021-22204', 'CVE-2020-1472']
};

fetch(url, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify(data)
})
  .then(response => response.json())
  .then(result => {
    if (!result.error) {
      result.data.results.forEach(item => {
        console.log(`\nCVE ID: ${item.cve_id}`);
        console.log(`是否有数据: ${item.has_data}`);
        if (item.cves_table) {
          console.log(`基础分数: ${item.cves_table.base_score || 'N/A'}`);
          console.log(`严重级别: ${item.cves_table.base_severity || 'N/A'}`);
        }
      });
    } else {
      console.error(`错误: ${result.message}`);
    }
  })
  .catch(error => console.error('请求失败:', error));
```

## 5. 常见问题

### 5.1 CVE ID格式不正确

确保CVE ID符合`CVE-YYYY-NNNN`的标准格式，其中YYYY是年份，NNNN是漏洞编号。

### 5.2 查询结果为空

如果返回结果中所有表数据都为空，表示数据库中没有该CVE的相关信息。

### 5.3 批量查询限制

批量查询最多支持50个CVE ID，如果需要查询更多，请分批进行。

### 5.4 时区说明

所有时间字段均已转换为中国时区（UTC+8），便于国内用户使用。

## 6. 接口性能

- 单个CVE查询通常响应时间在100ms以内
- 批量查询响应时间随查询数量增加而增长，但通常在1秒内完成

## 7. 注意事项

- 请合理使用API，避免频繁请求导致服务过载
- 对于大量数据查询，建议使用批量查询接口以减少网络请求次数
- 如发现接口问题或有改进建议，请联系系统管理员