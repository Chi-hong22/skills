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

## 1 本周概述

[首段用不超过 120 字说明这是什么事、为什么难；随后 1-3 个短自然段写分析后形成的认识和判断：现在怎么看问题、关键问题是什么、下一步为什么这样做。实验数据在详细章节支撑判断，不能用读数清单代替分析结果；不编原因，不写过程，不使用分点；段尾不补白，不用第三方评价口吻。主要成果图可紧随概述展示。]

---

## 2 [优先使用用户指定或日志已有主题名称]

### 2.1 [直接说明当前判断；轻主题可省略此层]

- [首句用不超过 40 字说明该主题在整件事里的位置；随后先给分析判断，再用最少必要证据说明为什么；用导师无需阅读代码也能理解的话解释对象和关系；给导师问题阶段答案，保留必要条件和置信度。] 【日期·分类】

**表 1 [表的标题]**

| [列表头] | [列表头] | [列表头] |
| --- | --- | --- |
| [行] | [行] | [行] |

[选关键对照解释判断；数值表保留关键读数，定性图表说明关系即可。无必要图表时删除占位。]

**图 1 [图的标题]**

![[attachments/image.png]]

[1-2 句解读，说明图支撑了什么判断] 【日期·分类】

<!-- 小节按实际内容保留并顺序编号；独立阅读另设文献阅读章，不强行并入研究主题。 -->

### 2.2 当前问题

[仅写尚未闭合的待验证假设、暂无法解释的问题、成立条件、作用边界或证据缺口；每条须能指回日志里被卡住的具体位置，指不回就删除；与文末“存在问题与需与导师讨论的事项”重复时只在文末展开。没有实质问题时删除本节。]

### 2.3 下一验证

[只写要拿到什么证据或结果、什么条件会推翻当前判断；近期要区分什么、为什么，一句说清。不写步骤、参数与排期。]

---

## 5 存在问题与需与导师讨论的事项

[仅写需要导师裁定的具体取舍或可能改变判断的阻塞，每条一句；与主题内“当前问题”重复时只写在这里。没有则删除本节。]



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
    // 运行前按当前 Vault 的实际日志根目录设置；该路径只是旧示例，不代表已探测目录。
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
