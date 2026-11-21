# PCB 设计检查报告（脚本级）

- 板框：120.0 × 80.0 mm，2 层，1.6mm FR4，1oz 铜
- 最小走线：信号 0.30 mm，电源 0.40 mm
- 设计间距：0.15 mm（网格 0.5mm 近似）
- 过孔：0.6/0.3 mm，GND 过孔 + 信号换层过孔
- 焊盘：THT 1.7/1.0 mm，端子 2.2/1.3 mm

## 布线结果

| 网络 | 线段数 | 状态 |
|---|---|---|
| VBAT_SENSE | 31 | OK |
| 5V | 171 | OK |
| 3V3 | 109 | OK |
| 12V_RAIL | 124 | OK |
| 12V_IN | 10 | OK |
| 12V_FUSED | 3 | OK |
| I2C_SCL | 90 | OK |
| I2C_SDA | 92 | OK |
| SERVO | 112 | OK |
| RADAR_OUT | 110 | OK |
| RADAR_TX | 91 | OK |
| LED_R_CTRL | 96 | OK |
| RADAR_RX | 89 | OK |
| LDR_SENSE | 112 | OK |
| LED_B_CTRL | 104 | OK |
| DF_RX | 120 | OK |
| DF_TX | 104 | OK |
| STATUS_LED | 61 | OK |
| SPK+ | 51 | OK |
| BTN_TEST | 45 | OK |
| SPK- | 50 | OK |
| BTN_MODE | 37 | OK |
| LED_B_D | 15 | OK |
| DF_RX_MOD | 13 | OK |
| LED_R_D | 12 | OK |
| Q1_G | 6 | OK |
| Q2_G | 6 | OK |
| LED1_K | 2 | OK |
| LED2_A | 2 | OK |

- 顶/底层走线：890 / 988 段
- GND 过孔 10 个，信号过孔 52 个

## 未完成连接

无。所有信号网络均由 MST 边连接成功。

## 同层间距检查

- 比较线段总数：1878
- 同层异网间距违规：0 处
- 单焊盘网络：无

## 必须人工复核的项

1. 本板由脚本生成，未在 KiCad/Altium 中运行官方 DRC；打样前请导入 EDA 复核间距、焊盘与丝印。
2. 电源路径按 1A 设计；如喇叭长时间满功率，请把 5V 走线加宽到 0.8mm 或开窗加锡。
3. J3 已按 DFPlayer Mini 实物引脚排列：VCC / RX / TX / SPK1 / SPK2 / GND；RX 串 1k（R7）接 GPIO27，TX 接 GPIO26。
4. 底层为整板 GND 平面：非 GND 通孔按焊盘外形 +0.6mm 避让，底层走线两侧留 0.3mm 隔离槽，信号过孔 +0.6mm 避让；SMD 地焊盘通过 0.3mm 过孔下地。
5. 12V 输入建议外加自恢复保险丝与 TVS；本板已留 F1/D2 位置。
