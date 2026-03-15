#!/bin/bash
# 券商研报定时推送脚本
# 每天 7:38 执行

cd /Users/zhoujy/.openclaw/workspace

echo "[$(date)] 开始执行研报抓取..." >> /Users/zhoujy/.openclaw/workspace/report_cron.log

# 运行新的 Python 脚本
python3 /Users/zhoujy/.openclaw/workspace/report_fetcher.py > /tmp/report_output.txt 2>> /Users/zhoujy/.openclaw/workspace/report_cron.log

# 发送到飞书（通过 OpenClaw 消息通道）
if [ -f /tmp/report_output.txt ]; then
    # 读取内容并通过 OpenClaw 发送
    REPORT_CONTENT=$(cat /tmp/report_output.txt)
    echo "[$(date)] 研报内容已生成，长度: ${#REPORT_CONTENT}" >> /Users/zhoujy/.openclaw/workspace/report_cron.log
    
    # 这里可以添加发送到飞书的逻辑
    # 目前先保存到日志
    echo "$REPORT_CONTENT" >> /Users/zhoujy/.openclaw/workspace/report_cron.log
fi

echo "[$(date)] 执行完成" >> /Users/zhoujy/.openclaw/workspace/report_cron.log
