# Amadeus API 申请指南

## 简介
Amadeus 是全球领先的旅游技术公司，提供真实的航班、酒店、租车等数据 API。

**免费额度：**
- Flight Offers Search API: 2000 次/月
- 支持全球 400+ 航空公司
- 实时价格和可用性

---

## 申请步骤

### 第一步：访问官网
打开 https://developers.amadeus.com

### 第二步：注册账号
1. 点击右上角 **"Sign Up"** 或 **"Register"**
2. 填写注册信息：
   - **Email**: 470528113@qq.com
   - **Password**: （设置一个安全密码）
   - **First Name**: Jingyu
   - **Last Name**: Zhou
   - **Company**: Personal
   - **Country**: China
3. 勾选同意条款
4. 点击 **"Create Account"**

### 第三步：验证邮箱
1. 登录 QQ 邮箱（470528113@qq.com）
2. 查找来自 Amadeus 的验证邮件
3. 点击邮件中的验证链接

### 第四步：创建应用
1. 登录后点击 **"Create App"** 或 **"My Apps"**
2. 选择 **"Self-Service API"**（免费套餐）
3. 填写应用信息：
   - **App Name**: FlightPriceMonitor
   - **Description**: Personal flight price monitoring tool
   - **Environment**: Production
4. 点击 **"Create"**

### 第五步：获取 API Key
创建成功后，你会看到：
- **API Key**: （一串字符，如：xxxxxxxxxxxxxxxx）
- **API Secret**: （一串字符，如：yyyyyyyyyyyyyyyy）

**请复制保存这两个值！**

---

## API 使用示例

### 测试 API Key
```bash
curl "https://test.api.amadeus.com/v2/shopping/flight-offers?originLocationCode=PEK&destinationLocationCode=SHA&departureDate=2025-04-15&adults=1&max=5" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

### Python 代码示例
```python
from amadeus import Client, ResponseError

amadeus = Client(
    client_id='YOUR_API_KEY',
    client_secret='YOUR_API_SECRET'
)

try:
    response = amadeus.shopping.flight_offers_search.get(
        originLocationCode='PEK',
        destinationLocationCode='SHA',
        departureDate='2025-04-15',
        adults=1,
        max=5
    )
    print(response.data)
except ResponseError as error:
    print(error)
```

---

## 支持的 API

### 免费套餐包含：
- ✅ Flight Offers Search（机票搜索）
- ✅ Flight Offers Price（机票价格）
- ✅ Flight Inspiration Search（灵感搜索）
- ✅ Airport Routes（机场航线）
- ✅ Airline Routes（航空公司航线）

### 付费套餐（超出免费额度）：
- 每 1000 次调用约 $0.05-0.10

---

## 城市代码参考

| 城市 | IATA代码 |
|------|----------|
| 北京 | PEK |
| 上海 | SHA (虹桥) / PVG (浦东) |
| 广州 | CAN |
| 深圳 | SZX |
| 成都 | CTU |
| 杭州 | HGH |
| 大阪 | KIX |
| 东京 | NRT (成田) / HND (羽田) |
| 首尔 | ICN |
| 新加坡 | SIN |
| 曼谷 | BKK |
| 香港 | HKG |

---

## 下一步

获取 API Key 后，发给我：
1. API Key
2. API Secret

我会帮你：
- ✅ 集成到机票监测系统中
- ✅ 创建真实数据查询功能
- ✅ 设置自动价格监测

---

## 注意事项

1. **免费额度**：每月 2000 次调用，超出后需要付费
2. **测试环境**：建议先用 test.api.amadeus.com 测试
3. **生产环境**：正式使用使用 api.amadeus.com
4. **频率限制**：注意 API 调用频率，避免被封

---

## 帮助

如遇问题，可以：
- 查看官方文档：https://developers.amadeus.com/self-service/apis-docs/guides
- 联系支持：developers@amadeus.com
- 查看 GitHub 示例：https://github.com/amadeus4dev
