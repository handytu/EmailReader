import unittest
from app.email.code_extractor import extract_verification_code
from app.models.message import MailMessage


class CodeExtractorTests(unittest.TestCase):
    def test_x_confirmation_subject_wins_over_body_numbers(self):
        message = MailMessage('1', subject='Your X confirmation code is 040710',
            body_text='We noticed an attempt to log in. Login device 1355. Security code: 999999',
            body_html='<p>Enter the following single-use code.</p><h1>040710</h1>')
        self.assertEqual(extract_verification_code(message), '040710')

    def test_html_code_survives_partial_text_and_tracking_attributes(self):
        message = MailMessage('1', subject='Your X confirmation code',
            body_text='We noticed an attempt to login on device 1355.',
            body_html='<style>.x {width:123456px}</style><img src="https://x.com/987654">'
                      '<p>Enter this single-use code:</p><h1>040710</h1>')
        self.assertEqual(extract_verification_code(message), '040710')

    def test_short_code_and_year_shaped_explicit_code(self):
        for code in ['0012', '2026', '12345678']:
            with self.subTest(code=code):
                self.assertEqual(extract_verification_code(MailMessage('1', body_text=f'Your security code is {code}')), code)

    def test_reverse_code(self):
        self.assertEqual(extract_verification_code(MailMessage('1', body_text='654321 is your verification code')), '654321')

    def test_separate_heading_fallback(self):
        self.assertEqual(extract_verification_code(MailMessage('1', subject='Verify with your login code',
            body_html='<h1>002345</h1><p>This expires soon</p>')), '002345')

    def test_incidental_numbers_do_not_become_codes(self):
        for body in ['Login device 1355; IP 192.168.1.2', 'Security alert for 2026',
                     'Verify order 123456', 'Your verification code has expired. Visit https://x.com/123456',
                     'Your verification code expired in 2026. Device 1355',
                     'Your verification code: account123456@example.com',
                     'Your verification code: IP 123456.12.3.4']:
            with self.subTest(body=body):
                self.assertIsNone(extract_verification_code(MailMessage('1', body_text=body)))

    def test_ambiguous_fallback_is_not_guessed(self):
        self.assertIsNone(extract_verification_code(MailMessage('1', subject='Your verification code',
            body_text='Order 123456 and device 654321')))


if __name__ == '__main__':
    unittest.main()
