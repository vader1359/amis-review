insert into public.psi_exclusion_rules(source_type,match_field,operator,match_value,reason) values
 ('inventory','Tên kho','in','["KHO BÌNH PHÚ HÀNG LỖI (KHO ẢO)","KHO BÌNH PHÚ (KHO LỖI)","KHO CHỊ KATHY","KHO CHƯA XUẤT HÓA ĐƠN"]','Kho lỗi/ảo đã xác định'),
 ('inventory','LOẠI KHỎI TỒN KHO','truthy','true','Đã yêu cầu loại khỏi tồn kho'),
 ('purchase','F.O.C','in','["F.O.C","KHÔNG KHAI, PHÂN BỔ VÀO MÃ KHÁC"]','Dòng purchase đã xác định loại trừ'),
 ('purchase','Phân loại','in','["CLAIM","CAMPAIGN","MARKETING F.O.C","MARKETING MATERIAL","SHOWROOM","FDS","TEAM DỰ ÁN"]','Nhóm purchase không vào PSI');
