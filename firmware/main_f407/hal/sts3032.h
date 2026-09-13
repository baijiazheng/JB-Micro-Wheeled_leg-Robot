/**
 * @file    sts3032.h
 * @brief   FEETECH STS3032 串口舵机驱动 (同步写位置/速度/加速度)
 *
 * 单线半双工总线, 1Mbps。同步写指令格式:
 *   0xFF 0xFF 0xFE LEN 0x83 ADDR(41) NLEN(7)
 *   [ID][ACC][pos_lo][pos_hi][0][0][spd_lo][spd_hi]  ×N
 *   CHECKSUM
 *
 * 位置范围 0~4095 (对应 0~360°), 中心 2048。
 * 负值用 bit15 作符号位 (反转方向)。
 */

#ifndef STS3032_H
#define STS3032_H

#include <stdint.h>

typedef struct {
    uint8_t  id;        /* 舵机 ID (1 左, 2 右) */
    int16_t  position;  /* 目标位置 0~4095 */
    uint16_t speed;     /* 目标速度 (步/秒) */
    uint8_t  acc;       /* 加速度 */
} StsServoCmd;

/**
 * 构建同步写指令包 (SyncWritePosEx)。
 * @param cmds  舵机命令数组
 * @param n     舵机数量
 * @param buf   输出缓冲 (需 >= 7 + n*8 字节)
 * @return 包总长度 (字节)
 */
int sts3032_build_sync_write(const StsServoCmd *cmds, int n, uint8_t *buf);

#endif /* STS3032_H */
