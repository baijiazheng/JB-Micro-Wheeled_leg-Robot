# JB-Micro-Wheeled_leg-Robot

基于 [Micro-Wheeled_leg-Robot](https://gitee.com/lavine/Micro-Wheeled_leg-Robot)（穆世博/李育锋，开源）的 **STM32 双板 + CAN 复刻版**。

## 目标

- 双轮自平衡 + 腿部运动（跳跃）+ CAN 双板通信
- 元器件直接集成到两板，FOC 用 HAL 从零实现（不依赖 simpleFOC）
- 学习主线：STM32 HAL → FOC → LQR 平衡 → CAN → 双板架构

## 目录结构

```
├── docs/architecture.md        # 架构设计文档（唯一权威）
├── hardware/
│   ├── driver_board_f103/      # 驱动板（F103 + L6234 + AS5600 + MPU6050）
│   └── main_board_f407/        # 主控板（F407 + STS3032 + CAN）
├── firmware/
│   ├── driver_f103/            # 驱动板固件（FOC + 平衡 + CAN 从机）
│   └── main_f407/              # 主控板固件（腿 + CAN 主机）
└── mechanical/                 # 机械件（沿用参考的 STP 模型）
```

## 架构

```
驱动板 F103（运动控制层）  ←CAN→  主控板 F407（应用层）
  2×L6234 FOC                   2×STS3032 腿舵机
  2×AS5600 编码器                CAN 主机
  MPU6050 IMU                    状态机 + 未来 web
  LQR 平衡 + yaw
```

详见 [docs/architecture.md](docs/architecture.md)。

## 进度

- [x] 环境搭建（KiCad / STM32 工具链 / 立创EDA）
- [x] 参考项目分析 + 架构设计
- [ ] 双板原理图
- [ ] 双板 PCB
- [ ] 固件（FOC + 平衡 + CAN）
- [ ] 联调

## 参考

- 原项目：https://gitee.com/lavine/Micro-Wheeled_leg-Robot
- 视频：[自制首款桌面级双轮腿机器人](https://www.bilibili.com/video/BV1io4y1q73L/)
