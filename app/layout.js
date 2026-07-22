import './globals.css';

export const metadata = {
  title: 'NanoHome PSI Shared Tool',
  description: 'Nộp file nguồn, xử lý mismatch và tạo PSI Final dùng chung',
};

export default function RootLayout({ children }) {
  return (
    <html lang="vi">
      <body>{children}</body>
    </html>
  );
}
