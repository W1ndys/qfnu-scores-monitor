# 任务 Prompt：教务系统成绩监控与通知系统

## 角色设定：

你是一位拥有丰富后端架构经验和网络安全意识的全栈开发专家。当前项目中已经具备了基于 Python `requests` 和 `ddddocr` 的教务系统模拟登录能力。

## 任务目标：

基于现有的登录模块，开发一套「教务系统成绩监控与通知系统」。系统需要包含后台管理服务、前台用户界面、定时任务调度以及钉钉消息推送功能。

## 核心功能需求：

1.  **成绩监控与差异对比**：
    - 定时爬取目标教务系统的成绩页面。
    - 对比历史成绩，当发现新成绩时，触发通知流程。
2.  **消息推送**：
    - 集成钉钉机器人 Webhook。
    - 通知内容需包含：新出成绩的科目、分数、或系统状态通知（如登录过期）。
3.  **后台管理与前台交互**：
    - **前台**：提供用户登录界面，支持用户输入学号、密码、是否启用。必须显式展示《用户协议》和《安全声明》，告知用户系统仅存储 Session 用于自动查询，不保存学号密码，使用学号哈希进行用户标记用于存储序列化session和启用状态。
    - **后台**：管理用户列表、监控状态、手动触发检测等。
4.  **会话管理与安全机制（核心约束）**：
    - **零密码存储**：数据库中**严禁**存储用户的账号和明文密码。
    - **Session 存储方案**：用户首次登录后，仅提取 `requests.Session` 中的关键 Cookie 信息。
    - **加密存储**：将 Cookie 序列化后，使用高强度对称加密算法（如 AES-256-GCM）加密存储入库。
    - **解密使用**：仅在定时任务执行的内存生命周期内解密 Session 用于发起请求。
    - **密钥管理**：加密密钥应安全存储，避免硬编码在代码中，每个用户使用独立的随机生成的加密密钥存在数据库。
5.  **异常处理与过期重登**：
    - **过期检测逻辑**：在请求教务系统响应时，检测 Response Body 是否包含字符串 `“请输入验证码”`。
    - **过期处理**：一旦检测到上述字符串，标记该 Session 为过期，停止监控，并通过钉钉发送“登录过期提醒”，引导用户在前台重新登录以更新 Session。

## 技术栈建议：

- **后端**：Flask，配合 APScheduler 进行定时任务调度
- **数据库**：SQLite
- **前端**：Alpine.js 配合 Jinja2 模板
- **加密库**：Cryptography (Python)

## 教务系统相关API示例

### 获取成绩页面

#### 请求示例

```http
GET /jsxsd/kscj/cjcx_frm HTTP/1.1
Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7
Accept-Encoding: gzip, deflate
Accept-Language: zh-CN,zh;q=0.9
Cookie: JSESSIONID=54BBC679AA3E7F76480591F010D37CAE; sto-id-20480=CBLMMCMKFAAA; JSESSIONID=940A624ED5D686E2266409A8A88B14CF
Host: zhjw.qfnu.edu.cn
Proxy-Connection: keep-alive
Referer: http://zhjw.qfnu.edu.cn/jsxsd/framework/xsMain.jsp
Upgrade-Insecure-Requests: 1
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36
```

#### 响应示例

```html
HTTP/1.1 200 Connection: close Transfer-Encoding: chunked Cache-Control:
no-cache Content-Encoding: gzip Content-Language: zh-CN Content-Type:
text/html;charset=UTF-8 Date: Wed, 21 Jan 2026 09:35:54 GMT Expires: Thu, 01 Jan
1970 00:00:00 GMT Pragma: No-cache Vary: Accept-Encoding

<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
  <head id="headerid1">
    <base target="_self" />
    <title>课程成绩查询</title>
    <meta http-equiv="pragma" content="no-cache" />
    <meta http-equiv="cache-control" content="no-cache" />
    <meta http-equiv="expires" content="0" />
    <meta http-equiv="keywords" content="湖南强智科技教务系统" />
    <meta http-equiv="description" content="湖南强智科技教务系统" />
    <meta http-equiv="X-UA-Compatible" content="IE=EmulateIE8" />
    <script
      type="text/javascript"
      src="/jsxsd/js/jquery-1.8.0.min.js"
      language="javascript"></script>
    <script
      type="text/javascript"
      src="/jsxsd/js/jquery-min.js"
      language="javascript"></script>
    <script
      type="text/javascript"
      src="/jsxsd/js/common.js"
      language="javascript"></script>
    <script
      type="text/javascript"
      src="/jsxsd/js/iepngfix_tilebg.js"
      language="javascript"></script>
    <script
      type="text/javascript"
      src="/jsxsd/js/easyui/jquery.easyui.min.js"
      language="javascript"></script>
    <script
      type="text/javascript"
      src="/jsxsd/js/jquery.autocomplete.min.js"
      language="javascript"></script>
    <link
      href="/jsxsd/framework/images/common.css"
      rel="stylesheet"
      type="text/css" />
    <link
      href="/jsxsd/framework/images/blue.css"
      rel="stylesheet"
      type="text/css"
      id="link_theme" />
    <link
      href="/jsxsd/framework/images/workstation.css"
      rel="stylesheet"
      type="text/css" />
    <link href="/jsxsd/css/easyui.css" rel="stylesheet" type="text/css" />
    <link
      href="/jsxsd/css/jquery.autocomplete.css"
      rel="stylesheet"
      type="text/css" />
  </head>
  <iframe
    id="notSession"
    name="notSession"
    style="display: none;"
    src=""></iframe>
  <script type="text/javascript">
    jQuery(document).ready(function () {
      window.setInterval(
        function () {
          document.getElementById("notSession").src =
            "/jsxsd/framework/blankPage.jsp";
        },
        1000 * 60 * 10,
      );
    });
  </script>
  <body>
    <div class="">
      <div class="Nsb_layout_r">
        <!-- <table border="0" width="100%"    cellspacing="0" cellpadding="0"  id="Table2">

	</table> -->
        <table
          border="0"
          width="100%"
          cellspacing="0"
          cellpadding="0"
          id="Table2">
          <tr>
            <td id="frmtop">
              <iframe
                id="cjcx_query_frm"
                name="cjcx_query_frm"
                src="/jsxsd/kscj/cjcx_query"
                style="height:100px; VISIBILITY: inherit; WIDTH: 100%"
                frameborder="0"></iframe>
            </td>
          </tr>
          <tr>
            <td height="100%" id="frmtop">
              <iframe
                id="cjcx_list_frm"
                name="cjcx_list_frm"
                src="/jsxsd/kscj/cjcx_list?kksj=2025-2026-1"
                style="height:100%; VISIBILITY: inherit; WIDTH: 100%"
                frameborder="0"></iframe>
            </td>
          </tr>
        </table>
      </div>
    </div>
    <div
      id="showDiv"
      style="background-color: #999900; border: 1px double #000000; text-align: center; width: 220px; height: 60px; display: none; position: absolute;">
      <table cellpadding="0" cellspacing="0" width="100%" height="100%">
        <tr>
          <td height="60px;" style="color: #000000; font-size: 14px;">
            正在拼命加载中，请稍后...
          </td>
        </tr>
      </table>
    </div>

    <script language="javascript">
      window.onload = function () {
        var iframe = document.getElementById("cjcx_list_frm");
        document.getElementById("Table2").style.height =
          window.innerHeight - 5 + "px";
      };

      function pyfacjdy() {
        //$(window).height() - this.height()) / 2+$(window).scrollTop() + "px");
        jQuery("#showDiv")
          .css({
            left: (jQuery(window).width() - 220) / 2 + "px",
            top: (jQuery(window).height() - 60) / 2 + "px",
          })
          .show();
        window.location.href = "/jsxsd/kscj/facjdy_list";
      }
      function queryKscj() {
        /*if("" == $("#kksj").val()){
		alert("请选择开课时间!");
		return ;
	}*/
        document.forms["kscjQueryForm"].action = "/jsxsd/kscj/cjcx_list";
        document.forms["kscjQueryForm"].submit();
      }
      loadjs();
      function loadjs() {
        if ("" != "") {
          alert("");
        }
      }
    </script>
  </body>
</html>
```
