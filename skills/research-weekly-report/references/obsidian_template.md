---
<%*
const today = tp.date.now("YYYY-MM-DD");
const momentDate = window.moment(today, "YYYY-MM-DD", true);
const titleName = `周报_${momentDate.format("YYMMDD")}`;
const createTime = tp.file.creation_date("YYYY-MM-Do HH:mm:ss dddd");
const modificationDate = tp.file.last_modified_date("YYYY-MM-Do HH:mm:ss dddd");
-%>
标题: <% titleName %>
tags:
  - 日志/周报
创建时间:  <% createTime %>
编辑时间:  <% modificationDate %>
---

<!-- markdownlint-disable MD024 -->

# <% titleName %>

**时间范围**：[待核对：根据上一份周报与本次候选日志确定]
**关键进展摘要**：

- [待填充：摘要点1，体现本周核心突破]
- [待填充：摘要点2，体现思考与进步]

---

## 项目一：[项目名称]

**研究系统定位**：[待填充：说明该项目在整体研究系统中的位置、上游与下游关系]
**问题提出**：[待填充：说明本周聚焦的问题是什么、为什么提出] 【日期·分类】
**核心思考**：[待填充：说明当前判断、机理分析、假设或方案取舍依据] 【日期·分类】

### 1. 研究内容标题

[待填充：一句话概括]

### 2. 研究方法

- [待填充：算法/策略/实验设置，以及与问题提出的对应关系] 【日期·分类】

### 3. 技术路线

- [待填充：实现步骤] 【日期·分类】

### 4. 核心模型

- **模型架构**：[待填充]
- **关键改动**：[待填充：修改点或关键假设] 【日期·分类】

### 5. 仿真结果

- **核心指标/现象**：[待填充：数值或观察结论] 【日期·分类】
- 训练曲线见图1

### 6. 存在问题

- [待填充：工程/实验问题或当前局限] 【日期·分类】

### 7. 难点问题

- [待填充：理论/机制难点，以及为何尚未解决] 【日期·分类】

### 8. 解决思路

- [待填充：已尝试方案、下一步方案与选择依据] 【日期·分类】

### 9. 小论文撰写任务

- **本周进度**：[待填充] 【日期·分类】
- **下周计划**：[待填充]

---

## 附图索引

- **图1**：[待填充：描述] 【日期·分类】

![[attachments/image.png|描述]]



<%*
// --- 文件自动处理函数 ---

/**
 * 创建文件夹并移动当前文件
 */
async function setupFile() {
    // 重新获取日期信息，确保作用域安全
    const datePart = tp.date.now("YYMMDD");
    const titleName = `周报_${datePart}`;
    const year = tp.date.now("YYYY");
    const month = tp.date.now("MM");
    const destDir = `/04_自我管理/00_日志/${year}/${month}`;
    let finalPath = `${destDir}/${titleName}`;

    // 确保 Templater 已经创建了文件
    // 这是 Templater 的一个特性，需要等待文件实际写入磁盘
    const file = tp.file.find_tfile(tp.file.path(true));
    if (!file) {
      console.error("Templater 文件尚未创建，无法移动。");
      new Notice("错误：Templater 文件尚未创建，请重试。", 5000);
      return;
    }
    
    // 检查目标文件夹是否存在，不存在则创建
    if (!await tp.file.exists(destDir)) {
      await app.vault.createFolder(destDir);
    }

    // 安全性检查：如果目标文件已存在，则在文件名后附加时间戳
    if (await tp.file.exists(finalPath)) {
        const timestamp = tp.date.now("_HHmmss");
        finalPath = `${destDir}/${titleName}${timestamp}`;
        new Notice(`文件已存在，已重命名为：${titleName}${timestamp}.md`);
    }

    // 移动文件到目标文件夹
    await tp.file.move(finalPath);

    // 将光标定位到正文模板开头附近
    // 注意：cursor() 必须在文件移动后调用，因为它作用于"当前"文件
    tp.file.cursor(1); 
}

// --- 执行文件处理 ---
await setupFile();
-%>
