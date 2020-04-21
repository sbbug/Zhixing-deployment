# Zhixing Project

## Changelog (12.27) by Huang

- [x] 将最新的代码同步到master分支

## Changelog (12.25) by Huang

- [x] 将显示模块的更新同步到pytorch分支
- [ ] /window.py中疑似存在bug，无法正常退出？

## Changelog (12.20) by Huang

- [x] 加入pytorch版本的检测模型，只能在新的开发板上运行
- [x] 增加(/predictor.py)模块以简化主逻辑
- [x] 改动文件(/main.py,/functions.py,/configs/sample.yaml)，改动较大，请谨慎合并
- [ ] /window.py中疑似存在bug，无法正常退出？(pyautogui?)  

## Changelog (12.2) by Huang

- [x] 将显示模块合并到master分支
- [x] 优化部分代码段(/main.py)

## Changelog (12.1) by Wang

- [x] 将/main.py显示代码整理到/window.py中
- [x] 设置系统启动界面
- [x] 在/window.py中以线程方式显示界面，并监听键盘，同时把退出指令传给/main.py
- [x] 在/window.py实现简易当前帧检测类别数量
- [x] 在/window.py实例化win对象，保证/main.py简洁

## Changelog (11.29) by Huang

- [x] 修改显示字体 (/main.py)
- [x] 循环读取视频文件 (/utils/camera.py)

## Task (11.28) by Huang

- [ ] 显示界面模块化 (王开)
  - 修改文件：/window.py /main.py
- [ ] 评分模块　(孙宏伟)
  - 修改文件: /score/score.py /main.py
- [ ] 日志模块和其他 (黄中豪)
  - 修改文件：/utils/logger.py 等

git的管理是以文件为单位的。修改不同的文件肯定不会冲突，修改相同的文件则冲突的概率很大。
比如，我们都要修改/main.py，就会发生冲突，其他文件则基本不会冲突。

## TODO List (11.27)

- [ ] 显示界面模块化
  - 能否封装成类？
  - 仍使用OpenCV或者PyQt？
- [ ] 评分模块
  - 从检测模型得到的结果得到评分（多项式计算，根据客户要求）
  - 将包括评分在内的内容传到界面显示？
  - 保存到磁盘？
  - 调网络进行发送？
- [ ] 网络通信模块
- [ ] 一些技术细节
  - 初始化时间太长，能否优化？
  - 日志模块：除了系统工作日志，还包含tensorflow等的输出，能否将其禁用，或者分开输出到不同的log文件？
  - 很多地方还需要捕获异常，并将其输入到日志中，同时分为（INFO,WARNING,ERROR等级别）？