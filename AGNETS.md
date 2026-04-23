# 角色
你是一个 INTJ 的程序员开发。


## 项目信息

- 它本质上是一个 Palworld 存档编辑工具箱：底层负责解析/压缩 .sav，中层把世界数据组织成可操作的 Python 结构，上层提供一个比较大的 PySide6 图形界面来做玩家、公会、基地、地图、角色迁移等
    操作。
  - 这个仓库不是“单一 GUI 程序”，而是“一个底层存档库 + 一套 GUI 管理器 + 若干独立工具脚本”的组合。

  整体结构

  - README.md：功能总览很全，项目定位就是 “all-in-one save editor / fixer / transfer tool”。
  - pyproject.toml：依赖很明确，核心是 PySide6、numpy、pandas、cityhash、pyooz、loguru，要求 Python >=3.11。
  - src/palworld_save_tools：底层存档格式处理，负责 .sav <-> GVAS <-> JSON。
  - src/palworld_aio：主应用，AIO GUI、保存/加载、地图、玩家/公会/基地管理都在这里。
  - src/palworld_toolsets：一些独立工具，比如 host save 修复、slot injector、worldoption 转换等。
  - src/palworld_base_editor：基地编辑相关 UI/逻辑。
  - src/palworld_xgp_import：Game Pass / XGP 存档导入相关。
  - resources：图标、翻译、游戏数据字典、README 多语言版本。

  启动链路

  - start.py:29 会先确保本地有 .venv，然后安装核心依赖；start.py:52 再启动 src/bootup.py。
  - src/bootup.py 是二级启动器：负责启动前检查、依赖安装进度、splash/loading 体验，以及最后拉起主程序。
  - 真正的应用入口在 src/palworld_aio/main.py:84 的 run_aio()，并在 src/palworld_aio/main.py:253 启动。
  - src/palworld_aio/main.py 还有一个“命令行批处理模式”：如果直接传 Level.sav 路径，它会做日志扫描和自动清理，而不只是打开 GUI。

  核心数据流

  - src/palworld_save_tools/palsav.py:17 / src/palworld_save_tools/palsav.py:29 负责把 Palworld 的压缩存档解压/压回去。
  - src/palworld_save_tools/gvas.py:10 和 src/palworld_save_tools/gvas.py:76 定义了 GVAS 头和文件结构，也就是项目的“二进制存档抽象层”。
  - src/palworld_aio/utils.py:112 的 sav_to_gvas_wrapper() 会把 Level.sav 读成内存里的包装对象；src/palworld_aio/utils.py:125 再把它写回 .sav。
  - src/palworld_aio/save_manager.py:35 的 load_save() 是 GUI 侧真正的加载总入口：校验 Level.sav、读取 Players/、解析世界数据、构建缓存、扫描玩家/帕鲁/公会/基地信息。
  - src/palworld_aio/save_manager.py:163 的 save_changes() 负责备份并落盘。
  - 项目把“当前打开的世界”保存在全局状态里，比如 src/palworld_aio/constants.py:50 的 current_save_path 和 src/palworld_aio/constants.py:51 的 loaded_level_json。

  架构上的关键理解

  - 这是一个“以内存中的巨大世界 JSON/对象树为中心”的程序。加载后，大部分功能都直接修改这棵树，然后再统一写回。
  - src/palobject.py:183 的 MappingCacheObject 是很关键的缓存/索引层，它把世界里的 GroupSaveDataMap、BaseCampSaveData 等结构转成更容易访问的映射。
  - src/palworld_aio/constants.py 里有大量全局共享状态，所以这个项目更像“桌面应用架构”而不是“纯函数式库架构”。
  - 业务逻辑是按功能拆成 manager 的：例如 save_manager、guild_manager、player_manager、base_manager、inventory_manager、func_manager。其中 func_manager 更像“杂项批量修复/清理操作中心”。

  你可以把它理解成三层

  - 底层格式层：src/palworld_save_tools
      - 关心二进制格式、GVAS、压缩算法、JSON 转换。
  - 中间业务层：src/palworld_aio/*manager.py、src/palobject.py
      - 关心玩家、公会、基地、容器、动态物品、非法数据清理。
  - 表现层：src/palworld_aio/ui、src/palworld_aio/widgets
      - 关心窗口、标签页、地图视图、弹窗、搜索、状态面板。

  这个项目目前给我的印象

  - 优点：
      - 功能覆盖很广，README 写得也比较清楚。
      - 入口链路和主要职责划分基本清晰。
      - 既支持 GUI，也保留了底层 CLI/转换能力。
  - 特点/代价：
      - 全局状态很多，理解时要一直跟着 constants 走。
      - 模块数量大，很多操作不是“一个函数做完”，而是 UI -> manager -> utils -> save structure 串起来。
      - 偏实用工程，重视“能修存档/能迁移/能批处理”，不是特别偏向高内聚的小而美设计。

  如果你接下来要继续读，我建议按这个顺序

  1. 先看 README.md
  2. 再看 start.py -> src/bootup.py -> src/palworld_aio/main.py
  3. 然后看 src/palworld_aio/save_manager.py
  4. 再看 src/palworld_save_tools/palsav.py、src/palworld_save_tools/gvas.py
  5. 最后按需求进入 guild_manager / player_manager / base_manager / func_manager